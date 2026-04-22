"""Supabase-backed drug lookup service — replaces CSV loading with Postgres queries.

Switches seamlessly between CSV mode (local dev) and Supabase mode (production).
The chatbot always talks to `drug_lookup` — the underlying source is an implementation detail.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from supabase import create_client

from app.core.config import settings
from app.services.drug.lookup import (
    CeilingPriceInfo,
    DrugResult,
    GenericAlternative,
    LookupResult,
    StoreResult,
)


class SupabaseDrugLookup:
    """Drug lookup backed by Supabase Postgres — no CSV files needed."""

    _client = None
    _loaded = False

    @property
    def client(self):
        if self._client is None:
            self._client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_secret_key,
            )
        return self._client

    def load(self):
        """Nothing to pre-load — all queries are on-demand."""
        self._loaded = True

    # ─────────────────────────────────────────────────────────────────────────
    # Search — fuzzy brand name match via trigram index
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def _brand_name_set(self) -> set:
        """Lazy-built set of lowercase brand names for fast exact-match lookup."""
        if not hasattr(self, "__brand_name_set"):
            resp = self.client.table("drugs").select("brand_name").limit(5000).execute()
            object.__setattr__(self, "_SupabaseDrugLookup__brand_name_set", {r["brand_name"].lower() for r in resp.data})
        return getattr(self, "_SupabaseDrugLookup__brand_name_set", set())

    def search(self, query: str, salt_hint: str | None = None, limit: int = 100) -> list[dict]:
        """Search drugs by brand name using ILIKE and trigram fallback."""
        if not self._loaded:
            self.load()

        query_lower = query.lower().strip()
        query_words = query_lower.split()

        # Strategy 1: exact brand match
        if query_lower in self._brand_name_set:
            hits = self.client.table("drugs").select(
                "id, brand_name, manufacturer, salt_id, strength, dosage_form, pack_size, mrp, price_per_unit"
            ).eq("brand_name", query.title()).limit(limit).execute()
            if hits.data:
                return hits.data

        # Strategy 2: first word match (3+ chars)
        if query_words and len(query_words[0]) >= 3:
            first = query_words[0]
            hits = self.client.table("drugs").select(
                "id, brand_name, manufacturer, salt_id, strength, dosage_form, pack_size, mrp, price_per_unit"
            ).ilike("brand_name", f"{first}%").limit(limit).execute()
            if hits.data:
                return hits.data

        # Strategy 3: salt name match (when query looks like a salt)
        salt = self.client.table("salts").select("id, name").ilike("name", f"%{query_lower}%").limit(1).execute()
        if salt.data:
            salt_id = salt.data[0]["id"]
            hits = self.client.table("drugs").select(
                "id, brand_name, manufacturer, salt_id, strength, dosage_form, pack_size, mrp, price_per_unit"
            ).eq("salt_id", salt_id).limit(limit).execute()
            if hits.data:
                return hits.data

        # Strategy 4: substring / trigram match (ILIKE)
        hits = self.client.table("drugs").select(
            "id, brand_name, manufacturer, salt_id, strength, dosage_form, pack_size, mrp, price_per_unit"
        ).ilike("brand_name", f"%{query_lower}%").limit(limit).execute()
        return hits.data

    def _brand_index_loaded(self) -> set:
        """Build in-memory set of exact brand names for fast lookup."""
        if not hasattr(self, "_brand_name_set"):
            resp = self.client.table("drugs").select("brand_name").limit(5000).execute()
            self._brand_name_set = {r["brand_name"].lower() for r in resp.data}
        return self._brand_name_set

    # ─────────────────────────────────────────────────────────────────────────
    # Pick best match — uses the same scoring logic as CSV version
    # ─────────────────────────────────────────────────────────────────────────
    def _pick_best_match(self, query: str, hits: list[dict], salt_hint: str | None = None) -> dict:
        query_lower = query.lower().strip()
        query_words = query_lower.split()

        strength_hint = ""
        for w in query_words:
            m = re.match(r"(\d+)", w)
            if m:
                strength_hint = m.group(1)
                break

        hint_salt_id = None
        if salt_hint:
            salt_resp = self.client.table("salts").select("id").eq("name", salt_hint).limit(1).execute()
            if salt_resp.data:
                hint_salt_id = salt_resp.data[0]["id"]

        best = None
        best_score = -1

        for d in hits:
            name_lower = d["brand_name"].lower()
            score = 0

            if hint_salt_id and d.get("salt_id") == hint_salt_id:
                score += 500
                strength_val = d.get("strength", "")
                if "/" in strength_val:
                    score -= 200
                dose_numbers = re.findall(r"\d+(?:\.\d+)?", name_lower)
                if len(dose_numbers) > 1:
                    score -= 150

            if name_lower == query_lower:
                score += 1000
            if name_lower.startswith(query_words[0]):
                score += 100

            word_matches = sum(1 for w in query_words if w in name_lower)
            score += word_matches * 20

            if strength_hint:
                drug_strength = d.get("strength", "")
                sm = re.match(r"(\d+)", drug_strength)
                if sm and sm.group(1) == strength_hint:
                    score += 150
                elif strength_hint in drug_strength:
                    score += 50

            mrp = float(d.get("mrp", 0))
            if 20 <= mrp <= 200:
                score += 5
            score += mrp / 100000

            if score > best_score:
                best_score = score
                best = d

        return best or hits[0]

    # ─────────────────────────────────────────────────────────────────────────
    # Full lookup
    # ─────────────────────────────────────────────────────────────────────────
    def lookup(self, query: str, pin_code: str | None = None, salt_hint: str | None = None) -> LookupResult:
        self.load()

        hits = self.search(query, salt_hint=salt_hint, limit=200)
        if not hits:
            return LookupResult(query=query, matched=False)

        top = self._pick_best_match(query, hits, salt_hint=salt_hint)

        # Get salt name
        salt_resp = self.client.table("salts").select("name").eq("id", top["salt_id"]).limit(1).execute()
        salt_name = salt_resp.data[0]["name"] if salt_resp.data else "Unknown"

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

        # Find generics
        brand_mrp = drug.mrp
        brand_strength = drug.strength
        salt_id = top["salt_id"]

        gen_resp = self.client.table("drugs").select(
            "id, brand_name, manufacturer, strength, dosage_form, pack_size, mrp, price_per_unit"
        ).eq("salt_id", salt_id).eq("strength", brand_strength).neq("id", top["id"]).lt("mrp", brand_mrp).order(
            "mrp", desc=False
        ).limit(20).execute()

        generics = []
        for g in gen_resp.data:
            savings = brand_mrp - float(g["mrp"])
            savings_pct = (savings / brand_mrp * 100) if brand_mrp > 0 else 0
            generics.append(GenericAlternative(
                brand_name=g["brand_name"],
                manufacturer=g.get("manufacturer", ""),
                mrp=float(g["mrp"]),
                pack_size=g.get("pack_size", ""),
                price_per_unit=float(g.get("price_per_unit") or 0),
                savings_amount=round(savings, 2),
                savings_percent=round(savings_pct, 1),
            ))

        cheapest = generics[0] if generics else None

        # NPPA ceiling price
        ceiling_resp = self.client.table("nppa_ceiling_prices").select(
            "ceiling_price, dosage_form, strength"
        ).eq("salt_name", salt_name).limit(1).execute()
        ceiling = None
        if ceiling_resp.data:
            cp = ceiling_resp.data[0]
            ceiling = CeilingPriceInfo(
                ceiling_price=float(cp["ceiling_price"]),
                dosage_form=cp.get("dosage_form", ""),
                strength=cp.get("strength", ""),
            )

        # Stores
        stores = []
        if pin_code:
            store_resp = self.client.rpc(
                "find_stores_by_pin_with_prefix",
                {"pin": pin_code, "store_limit": 5}
            ).execute()
            for s in (store_resp.data or []):
                stores.append(StoreResult(
                    store_code=s["store_code"],
                    address=s.get("address", ""),
                    district=s.get("district", ""),
                    state=s.get("state", ""),
                    pin_code=s.get("pin_code", ""),
                    phone=s.get("phone", ""),
                ))

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

    def find_stores_by_pin(self, pin_code: str, limit: int = 5) -> list[StoreResult]:
        self.load()
        resp = self.client.rpc(
            "find_stores_by_pin_with_prefix",
            {"pin": pin_code, "store_limit": limit}
        ).execute()
        stores = []
        for s in (resp.data or []):
            stores.append(StoreResult(
                store_code=s["store_code"],
                address=s.get("address", ""),
                district=s.get("district", ""),
                state=s.get("state", ""),
                pin_code=s.get("pin_code", ""),
                phone=s.get("phone", ""),
            ))
        return stores


# Singleton — used by chatbot
supabase_drug_lookup = SupabaseDrugLookup()