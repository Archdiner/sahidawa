"""Async Supabase-backed drug lookup — parallel queries, caching, minimal latency."""

from __future__ import annotations

import asyncio
import concurrent.futures
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx
from supabase import create_client

from app.core.config import settings
from app.services.cache import cached_llm_parse, _drug_lookup_cache

if TYPE_CHECKING:
    from app.services.drug.lookup import (
        CeilingPriceInfo,
        DrugResult,
        GenericAlternative,
        LookupResult,
        StoreResult,
    )
else:
    from app.services.drug.lookup import (
        CeilingPriceInfo,
        DrugResult,
        GenericAlternative,
        LookupResult,
        StoreResult,
    )


class AsyncSupabaseLookup:
    """Async, parallelized Supabase queries for minimum latency."""

    _client = None

    @property
    def client(self):
        if self._client is None:
            self._client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_secret_key,
            )
        return self._client

    def load(self):
        pass  # Nothing to pre-load

    # ─────────────────────────────────────────────────────────────────────────
    # Parallel search: brand + salt name in one round-trip
    # ─────────────────────────────────────────────────────────────────────────
    async def _search_drugs_parallel(self, query: str, limit: int = 200) -> list[dict]:
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        base_url = self.client.rest_url
        key = self.client.supabase_key
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}

        async with httpx.AsyncClient(timeout=15.0) as http:
            tasks = []

            # Strategy 1: exact brand match
            if query_lower:
                tasks.append(
                    http.get(
                        f"{base_url}/drugs",
                        params={"brand_name": f"eq.{query.title()}", "select": "id,brand_name,manufacturer,salt_id,strength,dosage_form,pack_size,mrp,price_per_unit", "limit": limit},
                        headers=headers,
                    )
                )

            # Strategy 2: first-word prefix match
            if query_words and len(query_words[0]) >= 3:
                first = query_words[0]
                tasks.append(
                    http.get(
                        f"{base_url}/drugs",
                        params={"brand_name": f"ilike.{first}%", "select": "id,brand_name,manufacturer,salt_id,strength,dosage_form,pack_size,mrp,price_per_unit", "limit": limit},
                        headers=headers,
                    )
                )

            # Strategy 3: salt name match (ILIKE on salts table → join)
            tasks.append(
                http.get(
                    f"{base_url}/salts",
                    params={"name": f"ilike.*{query_lower}*", "select": "id,name", "limit": 1},
                    headers=headers,
                )
            )

            # Strategy 4: general ILIKE
            tasks.append(
                http.get(
                    f"{base_url}/drugs",
                    params={"brand_name": f"ilike.*{query_lower}*", "select": "id,brand_name,manufacturer,salt_id,strength,dosage_form,pack_size,mrp,price_per_unit", "limit": limit // 4},
                    headers=headers,
                )
            )

            responses = await asyncio.gather(*tasks, return_exceptions=True)

        hits = []
        seen_ids = set()

        # Process exact/prefix results
        for resp in responses[:2]:
            if isinstance(resp, Exception):
                continue
            if resp.status_code == 200:
                for d in resp.json():
                    if d["id"] not in seen_ids:
                        seen_ids.add(d["id"])
                        hits.append(d)

        # Salt match — may need second request to get drugs
        salt_resp = responses[2]
        if isinstance(salt_resp, httpx.Response) and salt_resp.status_code == 200:
            salts = salt_resp.json()
            if salts:
                salt_id = salts[0]["id"]
                async with httpx.AsyncClient(timeout=15.0) as http:
                    salt_resp2 = await http.get(
                        f"{base_url}/drugs",
                        params={"salt_id": f"eq.{salt_id}", "select": "id,brand_name,manufacturer,salt_id,strength,dosage_form,pack_size,mrp,price_per_unit", "limit": limit // 2},
                        headers=headers,
                    )
                    if salt_resp2.status_code == 200:
                        for d in salt_resp2.json():
                            if d["id"] not in seen_ids:
                                seen_ids.add(d["id"])
                                hits.append(d)

        # ILIKE fallback
        ilike_resp = responses[3]
        if isinstance(ilike_resp, httpx.Response) and ilike_resp.status_code == 200:
            for d in ilike_resp.json():
                if d["id"] not in seen_ids:
                    seen_ids.add(d["id"])
                    hits.append(d)

        return hits

    # ─────────────────────────────────────────────────────────────────────────
    # Parallel: generics + ceiling + stores all fired simultaneously
    # ─────────────────────────────────────────────────────────────────────────
    async def _fetch_related_parallel(
        self,
        salt_id: str,
        salt_name: str,
        brand_mrp: float,
        brand_strength: str,
        brand_id: str,
        pin_code: str | None,
    ) -> tuple[list[dict], dict | None, list[dict]]:
        base_url = self.client.rest_url
        key = self.client.supabase_key
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}

        async with httpx.AsyncClient(timeout=15.0) as http:
            tasks = []
            task_names = []

            # Generics: same salt+strength, cheaper
            tasks.append(http.get(
                f"{base_url}/drugs",
                params={
                    "salt_id": f"eq.{salt_id}",
                    "strength": f"eq.{brand_strength}",
                    "mrp": f"lt.{brand_mrp}",
                    "id": f"neq.{brand_id}",
                    "select": "id,brand_name,manufacturer,strength,dosage_form,pack_size,mrp,price_per_unit",
                    "order": "mrp.asc",
                    "limit": 20,
                },
                headers=headers,
            ))
            task_names.append("generics")

            # Ceiling price
            tasks.append(http.get(
                f"{base_url}/nppa_ceiling_prices",
                params={
                    "salt_name": f"eq.{salt_name}",
                    "select": "ceiling_price,dosage_form,strength",
                    "limit": 1,
                },
                headers=headers,
            ))
            task_names.append("ceiling")

            # Stores (if pin provided)
            if pin_code:
                tasks.append(http.post(
                    f"{base_url}/rpc/find_stores_by_pin_with_prefix",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"pin": pin_code, "store_limit": 5},
                ))
                task_names.append("stores")

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse generics
        generics_data = []
        generics_resp = results[0]
        if not isinstance(generics_resp, Exception) and generics_resp.status_code == 200:
            for g in generics_resp.json():
                savings = brand_mrp - float(g["mrp"])
                savings_pct = (savings / brand_mrp * 100) if brand_mrp > 0 else 0
                generics_data.append(GenericAlternative(
                    brand_name=g["brand_name"],
                    manufacturer=g.get("manufacturer", ""),
                    mrp=float(g["mrp"]),
                    pack_size=g.get("pack_size", ""),
                    price_per_unit=float(g.get("price_per_unit") or 0),
                    savings_amount=round(savings, 2),
                    savings_percent=round(savings_pct, 1),
                ))

        # Parse ceiling
        ceiling = None
        ceiling_resp = results[1]
        if not isinstance(ceiling_resp, Exception) and ceiling_resp.status_code == 200:
            cp_data = ceiling_resp.json()
            if cp_data:
                cp = cp_data[0]
                ceiling = CeilingPriceInfo(
                    ceiling_price=float(cp["ceiling_price"]),
                    dosage_form=cp.get("dosage_form", ""),
                    strength=cp.get("strength", ""),
                )

        # Parse stores
        stores = []
        if pin_code and len(results) > 2:
            stores_resp = results[2]
            if not isinstance(stores_resp, Exception) and stores_resp.status_code == 200:
                for s in stores_resp.json():
                    stores.append(StoreResult(
                        store_code=s["store_code"],
                        address=s.get("address", ""),
                        district=s.get("district", ""),
                        state=s.get("state", ""),
                        pin_code=s.get("pin_code", ""),
                        phone=s.get("phone", ""),
                    ))

        return generics_data, ceiling, stores

    # ─────────────────────────────────────────────────────────────────────────
    # Scoring (same logic as CSV version)
    # ─────────────────────────────────────────────────────────────────────────
    def _score_drug(self, drug: dict, query: str, salt_hint: str | None = None, hint_salt_id: str | None = None) -> int:
        name_lower = drug["brand_name"].lower()
        query_lower = query.lower().strip()
        query_words = query_lower.split()

        score = 0

        # Salt hint bonus
        if hint_salt_id and drug.get("salt_id") == hint_salt_id:
            score += 500
            if "/" in drug.get("strength", ""):
                score -= 200
            dose_numbers = re.findall(r"\d+(?:\.\d+)?", name_lower)
            if len(dose_numbers) > 1:
                score -= 150

        # Exact brand match
        if name_lower == query_lower:
            score += 1000

        # Prefix match
        if query_words and name_lower.startswith(query_words[0]):
            score += 100

        # Word matches
        score += sum(1 for w in query_words if w in name_lower) * 20

        # Strength hint
        strength_hint = ""
        for w in query_words:
            m = re.match(r"(\d+)", w)
            if m:
                strength_hint = m.group(1)
                break
        if strength_hint:
            drug_strength = drug.get("strength", "")
            sm = re.match(r"(\d+)", drug_strength)
            if sm and sm.group(1) == strength_hint:
                score += 150
            elif strength_hint in drug_strength:
                score += 50

        # Price sweet spot
        mrp = float(drug.get("mrp", 0))
        if 20 <= mrp <= 200:
            score += 5
        score += mrp / 100000

        return score

    def _pick_best(self, query: str, hits: list[dict], salt_hint: str | None = None, hint_salt_id: str | None = None) -> dict | None:
        if not hits:
            return None
        scored = [(self._score_drug(d, query, salt_hint, hint_salt_id), d) for d in hits]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    # ─────────────────────────────────────────────────────────────────────────
    # Main lookup — fires all DB queries in parallel
    # ─────────────────────────────────────────────────────────────────────────
    async def alookup(
        self,
        query: str,
        pin_code: str | None = None,
        salt_hint: str | None = None,
        llm_parse_fn=None,
    ) -> LookupResult:
        """Async full lookup: parse → search → score → parallel fetch generics/ceiling/stores."""

        # Optional LLM parse with caching
        llm_result = None
        if llm_parse_fn:
            llm_result = cached_llm_parse(query, llm_parse_fn)
            if llm_result:
                if not llm_result.get("drug_name") and not llm_result.get("salt_composition"):
                    return LookupResult(query=query, matched=False)
                # Use LLM-parsed values
                if not salt_hint and llm_result.get("salt_composition"):
                    salt_hint = llm_result["salt_composition"]

        # Step 1: parallel search
        hits = await self._search_drugs_parallel(query)

        if not hits:
            return LookupResult(query=query, matched=False)

        # Resolve hint salt_id for scoring
        hint_salt_id = None
        if salt_hint:
            base_url = self.client.rest_url
            key = self.client.supabase_key
            headers = {"apikey": key, "Authorization": f"Bearer {key}"}
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.get(
                    f"{base_url}/salts",
                    params={"name": f"ilike.*{salt_hint}*", "select": "id", "limit": 1},
                    headers=headers,
                )
                if resp.status_code == 200 and resp.json():
                    hint_salt_id = resp.json()[0]["id"]

        top = self._pick_best(query, hits, salt_hint, hint_salt_id)
        if not top:
            return LookupResult(query=query, matched=False)

        # Get salt name
        base_url = self.client.rest_url
        key = self.client.supabase_key
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(timeout=10.0) as http:
            salt_resp = await http.get(
                f"{base_url}/salts",
                params={"id": f"eq.{top['salt_id']}", "select": "name", "limit": 1},
                headers=headers,
            )
            salt_name = salt_resp.json()[0]["name"] if salt_resp.status_code == 200 and salt_resp.json() else "Unknown"

        drug = DrugResult(
            brand_name=top["brand_name"],
            salt_name=salt_name,
            strength=top.get("strength", ""),
            dosage_form=top.get("dosage_form", ""),
            manufacturer=top.get("manufacturer", ""),
            mrp=float(top.get("mrp", 0)),
            pack_size=top.get("pack_size", ""),
            price_per_unit=float(top.get("price_per_unit") or 0),
        )

        # Step 2: parallel fetch of generics + ceiling + stores
        generics, ceiling, stores = await self._fetch_related_parallel(
            salt_id=top["salt_id"],
            salt_name=salt_name,
            brand_mrp=drug.mrp,
            brand_strength=drug.strength,
            brand_id=top["id"],
            pin_code=pin_code,
        )

        cheapest = generics[0] if generics else None

        return LookupResult(
            query=query,
            matched=True,
            drug=drug,
            generics=generics,
            cheapest=cheapest,
            total_alternatives=len(generics),
            ceiling_price=ceiling,
            nearby_stores=stores,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Sync wrapper with caching
    # ─────────────────────────────────────────────────────────────────────────
    def lookup(self, query: str, pin_code: str | None = None, salt_hint: str | None = None, llm_parse_fn=None) -> LookupResult:
        """Sync wrapper — runs the async lookup in a thread pool."""
        from app.services.cache import cached_drug_lookup

        key_query = query.strip().lower()
        cache_key = f"{key_query}|{pin_code or ''}"

        # Check cache first (sync, fast)
        hit = _drug_lookup_cache.get(cache_key)
        if hit is not None:
            return hit

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.alookup(query, pin_code, salt_hint, llm_parse_fn)
                )
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future = executor.submit(_run)
            result = future.result(timeout=30)

        # Cache positive matches
        if result.matched:
            _drug_lookup_cache.set(cache_key, result)
        return result

    def find_stores_by_pin(self, pin_code: str, limit: int = 5) -> list:
        """Find Jan Aushadhi stores by pin code (sync, uses Supabase REST)."""
        base_url = self.client.rest_url
        key = self.client.supabase_key
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}

        resp = httpx.post(
            f"{base_url}/rpc/find_stores_by_pin_with_prefix",
            headers={**headers, "Content-Type": "application/json"},
            json={"pin": pin_code, "store_limit": limit},
            timeout=10,
        )

        stores = []
        if resp.status_code == 200:
            for s in (resp.json() or []):
                stores.append(StoreResult(
                    store_code=s["store_code"],
                    address=s.get("address", ""),
                    district=s.get("district", ""),
                    state=s.get("state", ""),
                    pin_code=s.get("pin_code", ""),
                    phone=s.get("phone", ""),
                ))
        return stores


# Singleton
async_supabase_lookup = AsyncSupabaseLookup()