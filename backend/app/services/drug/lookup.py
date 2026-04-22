"""Core drug lookup service — the heart of the product.

Handles: query → parse → search → find generics → find stores → format response.
Works in two modes:
  1. DB mode: queries PostgreSQL + Meilisearch (production)
  2. CSV mode: reads from processed CSVs (local testing, no services needed)
"""

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# __file__ = backend/app/services/drug/lookup.py
# In Vercel: data lives inside backend/data/
# Locally: data lives at project_root/data/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/
_PROJECT_ROOT = _BACKEND_ROOT.parent  # project root

# Prefer backend/data/ (Vercel), fall back to project_root/data/ (local dev)
if (_BACKEND_ROOT / "data" / "processed").exists():
    DATA_DIR = _BACKEND_ROOT / "data" / "processed"
    RAW_DIR = _BACKEND_ROOT / "data" / "raw"
else:
    DATA_DIR = _PROJECT_ROOT / "data" / "processed"
    RAW_DIR = _PROJECT_ROOT / "data" / "raw"


@dataclass
class DrugResult:
    brand_name: str
    salt_name: str
    strength: str
    dosage_form: str
    manufacturer: str
    mrp: float
    pack_size: str
    price_per_unit: float


@dataclass
class GenericAlternative:
    brand_name: str
    manufacturer: str
    mrp: float
    pack_size: str
    price_per_unit: float
    savings_amount: float
    savings_percent: float


@dataclass
class StoreResult:
    store_code: str
    address: str
    district: str
    state: str
    pin_code: str
    phone: str


@dataclass
class CeilingPriceInfo:
    ceiling_price: float
    dosage_form: str
    strength: str


@dataclass
class LookupResult:
    """Complete result for a single drug query."""
    query: str
    matched: bool
    drug: DrugResult | None = None
    generics: list[GenericAlternative] = field(default_factory=list)
    cheapest: GenericAlternative | None = None
    total_alternatives: int = 0
    ceiling_price: CeilingPriceInfo | None = None
    nearby_stores: list[StoreResult] = field(default_factory=list)
    is_narrow_therapeutic_index: bool = False


class DrugLookupService:
    """In-memory drug lookup from processed CSV files.

    Loaded once at startup, serves all queries from memory.
    """

    def __init__(self):
        self._salts: dict[str, dict] = {}       # id → {name, synonyms}
        self._salt_by_name: dict[str, str] = {}  # lowercase name → id
        self._drugs_by_salt: dict[str, list[dict]] = defaultdict(list)
        self._brand_index: dict[str, list[dict]] = defaultdict(list)  # lowercase brand → drugs
        self._nppa: dict[str, list[dict]] = defaultdict(list)  # salt_id → ceiling entries
        self._stores_by_pin: dict[str, list[dict]] = defaultdict(list)
        self._stores_by_state: dict[str, list[dict]] = defaultdict(list)
        self._loaded = False

    def load(self):
        """Load all data into memory from CSVs."""
        if self._loaded:
            return

        # Load salts
        salt_path = DATA_DIR / "salt_compositions.csv"
        if salt_path.exists():
            with open(salt_path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self._salts[row["id"]] = row
                    self._salt_by_name[row["name"].lower()] = row["id"]

        # Load drugs
        drugs_path = DATA_DIR / "drugs.csv"
        if drugs_path.exists():
            with open(drugs_path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self._drugs_by_salt[row["salt_id"]].append(row)
                    # Index by brand name words for fuzzy lookup
                    name_lower = row["brand_name"].lower()
                    self._brand_index[name_lower].append(row)
                    # Also index first word
                    first_word = name_lower.split()[0] if name_lower.split() else ""
                    if first_word and first_word != name_lower:
                        self._brand_index[first_word].append(row)

        # Load NPPA ceiling prices
        nppa_path = DATA_DIR / "nppa_matched.csv"
        if nppa_path.exists():
            with open(nppa_path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self._nppa[row["salt_id"]].append(row)

        # Load stores
        stores_path = RAW_DIR / "jan_aushadhi_stores.csv"
        if stores_path.exists():
            with open(stores_path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    pin = row.get("pin_code", "")
                    if pin:
                        self._stores_by_pin[pin].append(row)
                    state = row.get("state", "").lower()
                    if state:
                        self._stores_by_state[state].append(row)

        self._loaded = True

    def search(
        self, query: str, salt_hint: str | None = None, limit: int = 100
    ) -> list[dict]:
        """Search for drugs matching the query string.

        Returns results scored by relevance:
        - Exact full name match scores highest
        - First-word match next
        - Salt name match next
        - Substring match last (with strict guards)

        Args:
            salt_hint: optional salt/generic name from LLM parsing to boost results
            limit: max results to return (use higher for salt-name queries to capture
                   pure formulations buried by price sorting)
        """
        self.load()
        query_lower = query.lower().strip()
        query_words = query_lower.split()

        scored: list[tuple[int, dict]] = []
        seen_ids: set[str] = set()

        def _add(score: int, d: dict):
            did = d.get("id", "")
            if did not in seen_ids:
                seen_ids.add(did)
                scored.append((score, d))

        # Strategy 1: Exact brand name match (highest score)
        if query_lower in self._brand_index:
            for d in self._brand_index[query_lower]:
                _add(100, d)

        # Strategy 2: First word match (only if first word is 3+ chars)
        if not scored and query_words and len(query_words[0]) >= 3:
            first = query_words[0]
            if first in self._brand_index:
                for d in self._brand_index[first]:
                    name_lower = d["brand_name"].lower()
                    word_matches = sum(1 for w in query_words if w in name_lower)
                    _add(50 + word_matches * 10, d)

        # Strategy 3: Salt name match
        salt_id = self._salt_by_name.get(query_lower)
        if salt_id and not scored:
            for d in self._drugs_by_salt.get(salt_id, []):
                _add(80, d)

        # Strategy 3b: LLM salt hint — boost results matching the salt
        if salt_hint and not scored:
            hint_lower = salt_hint.lower().strip()
            hint_salt_id = self._salt_by_name.get(hint_lower)
            if hint_salt_id:
                for d in self._drugs_by_salt.get(hint_salt_id, []):
                    _add(75, d)

        # Strategy 4: Substring match — STRICT guards to avoid gibberish matches
        if not scored:
            # Only attempt substring if query is a real-looking drug name (3+ alpha chars)
            if len(query_lower) >= 3 and any(c.isalpha() for c in query_lower):
                for name, drugs in self._brand_index.items():
                    # Require the query to be a prefix of the brand name OR
                    # the brand name to start with query's first word (3+ chars)
                    first_word = query_words[0] if query_words else ""
                    is_prefix = name.startswith(query_lower)
                    is_first_word_prefix = (
                        len(first_word) >= 4 and name.startswith(first_word)
                    )
                    if is_prefix or is_first_word_prefix:
                        for d in drugs:
                            _add(30, d)
                        if len(scored) > 100:
                            break

        # Store salt_hint for use in combo penalty calculation
        self._last_salt_hint = salt_hint

        # Sort: score descending, -penalty ascending (lower penalty = purer = better, so -penalty is lower for purer)
        if salt_hint:
            scored.sort(key=lambda x: (x[0], -self._combo_penalty(x[1])))
        else:
            scored.sort(key=lambda x: (x[0], float(x[1].get("mrp", 0))), reverse=True)
        return [d for _, d in scored[:limit]]

    def _combo_penalty(self, drug: dict) -> float:
        """Return a penalty score for combo drugs (lower = better for salt queries)."""
        name_lower = drug.get("brand_name", "").lower()
        strength_val = drug.get("strength", "")
        penalty = 0.0
        # Penalize combo signatures
        if "/" in strength_val:
            penalty -= 200
        if "/" in name_lower and "mg" in name_lower:
            penalty -= 100
        dose_numbers = re.findall(r"\d+(?:\.\d+)?", name_lower)
        if len(dose_numbers) > 1:
            penalty -= 150
        # Bonus for brand name containing salt name hint
        salt_hint = getattr(self, "_last_salt_hint", "") or ""
        if salt_hint and salt_hint[:4] in name_lower:
            penalty += 50
        return penalty

    def _pick_best_match(
        self, query: str, hits: list[dict], salt_hint: str | None = None
    ) -> dict:
        """Pick the single best branded drug match from search hits.

        Prefers: salt hint match > exact name match > name contains query > highest price.
        Among ties, picks the popular branded version (higher price).
        """
        query_lower = query.lower().strip()
        query_words = query_lower.split()

        # Extract strength hint from query (e.g., "500" from "Crocin 500" or "500mg")
        strength_hint = ""
        for w in query_words:
            m = re.match(r"(\d+)", w)
            if m:
                strength_hint = m.group(1)  # just the numeric part
                break

        # Resolve salt_hint to salt_id for matching
        hint_salt_id = None
        if salt_hint:
            hint_salt_id = self._salt_by_name.get(salt_hint.lower().strip())

        best = None
        best_score = -1

        for d in hits:
            name_lower = d["brand_name"].lower()
            score = 0

            # Salt hint match — strong signal from LLM (e.g., Crocin → Paracetamol, not Caffeine)
            if hint_salt_id and d.get("salt_id") == hint_salt_id:
                score += 500
                # Penalize combo drugs (strength contains "/" like "10mg/160mg")
                strength_val = d.get("strength", "")
                if "/" in strength_val:
                    score -= 200
                # Penalize brand names that suggest combo (contain "mg/" or multiple dose numbers)
                if "/" in name_lower and "mg" in name_lower:
                    score -= 100
                # Bonus if brand name contains the salt/query name (likely a pure formulation)
                salt_name_hint = (salt_hint or "").lower()
                if salt_name_hint and salt_name_hint[:4] in name_lower:
                    score += 50
                # Penalize likely combos: brand names with secondary dose numbers
                # e.g., "Vozuca-M 0.3 Activ" has "0.3" indicating a second ingredient
                dose_numbers = re.findall(r"\d+(?:\.\d+)?", name_lower)
                if len(dose_numbers) > 1:
                    score -= 150

            # Exact full name match
            if name_lower == query_lower:
                score += 1000

            # Name starts with query
            if name_lower.startswith(query_words[0]):
                score += 100

            # All query words present in name
            word_matches = sum(1 for w in query_words if w in name_lower)
            score += word_matches * 20

            # Strength match bonus — check both the strength field and brand name
            if strength_hint:
                drug_strength = d.get("strength", "")
                # Exact strength match (e.g., "5mg" starts with "5" and is not "50mg")
                strength_num = re.match(r"(\d+)", drug_strength)
                if strength_num and strength_num.group(1) == strength_hint:
                    score += 150  # strong bonus for exact numeric match
                elif strength_hint in drug_strength:
                    score += 50  # partial (e.g., "5" in "500mg")
                elif strength_hint in name_lower:
                    score += 40

            # Prefer tablets over injections/infusions (more common user request)
            form = d.get("dosage_form", "").lower()
            if "tablet" in form:
                score += 10
            elif "capsule" in form:
                score += 8
            elif "syrup" in form:
                score += 5

            # Tiebreaker: moderate price preferred (too cheap = obscure, too expensive = combo/specialty)
            mrp = float(d.get("mrp", 0))
            if 20 <= mrp <= 200:
                score += 5  # sweet spot for common branded drugs
            score += mrp / 100000  # tiny tiebreaker for determinism

            if score > best_score:
                best_score = score
                best = d

        return best or hits[0]

    def lookup(
        self,
        query: str,
        pin_code: str | None = None,
        salt_hint: str | None = None,
    ) -> LookupResult:
        """Full lookup: find drug, generics, ceiling price, and nearby stores."""
        self.load()

        query_lower = query.lower().strip()
        is_salt_query = 500 if (
            query_lower in self._salt_by_name
            or (salt_hint and salt_hint.lower().strip() == query_lower)
            or (
                salt_hint
                and any(
                    salt_hint.lower().strip() in name
                    for name in self._brand_index.keys()
                )
            )
        ) else 100
        search_limit = is_salt_query if isinstance(is_salt_query, int) else 100

        hits = self.search(query, salt_hint=salt_hint, limit=search_limit)
        if not hits:
            return LookupResult(query=query, matched=False)

        # Pick the best match using smart ranking
        top = self._pick_best_match(query, hits, salt_hint=salt_hint)

        salt_id = top["salt_id"]
        salt_name = self._salts.get(salt_id, {}).get("name", "Unknown")
        brand_mrp = float(top.get("mrp", 0))
        brand_ppu = float(top.get("price_per_unit", 0))
        brand_strength = top.get("strength", "")

        drug = DrugResult(
            brand_name=top["brand_name"],
            salt_name=salt_name,
            strength=brand_strength,
            dosage_form=top.get("dosage_form", ""),
            manufacturer=top.get("manufacturer", ""),
            mrp=brand_mrp,
            pack_size=top.get("pack_size", ""),
            price_per_unit=brand_ppu,
        )

        # Find generics: same salt, same strength, cheaper
        all_same_salt = self._drugs_by_salt.get(salt_id, [])
        generics = []
        for d in all_same_salt:
            if d["id"] == top["id"]:
                continue
            d_mrp = float(d.get("mrp", 0))
            if d_mrp < brand_mrp and d.get("strength") == brand_strength:
                savings = brand_mrp - d_mrp
                savings_pct = (savings / brand_mrp * 100) if brand_mrp > 0 else 0
                generics.append(GenericAlternative(
                    brand_name=d["brand_name"],
                    manufacturer=d.get("manufacturer", ""),
                    mrp=d_mrp,
                    pack_size=d.get("pack_size", ""),
                    price_per_unit=float(d.get("price_per_unit", 0)),
                    savings_amount=round(savings, 2),
                    savings_percent=round(savings_pct, 1),
                ))

        generics.sort(key=lambda g: g.mrp)
        cheapest = generics[0] if generics else None

        # NPPA ceiling price
        ceiling = None
        nppa_entries = self._nppa.get(salt_id, [])
        for entry in nppa_entries:
            try:
                cp = float(entry.get("ceiling_price_2026", 0))
            except (ValueError, TypeError):
                continue
            if cp > 0:
                ceiling = CeilingPriceInfo(
                    ceiling_price=cp,
                    dosage_form=entry.get("dosage_form", ""),
                    strength=entry.get("strength", ""),
                )
                break

        # Nearby stores by pin code (with prefix fallback for geocoded pins that don't exactly match)
        stores = []
        if pin_code:
            found_stores = self.find_stores_by_pin(pin_code, limit=5)
            stores = found_stores

        return LookupResult(
            query=query,
            matched=True,
            drug=drug,
            generics=generics[:20],
            cheapest=cheapest,
            total_alternatives=len(generics),
            ceiling_price=ceiling,
            nearby_stores=stores,
        )

    def find_stores_by_pin(self, pin_code: str, limit: int = 5) -> list[StoreResult]:
        """Find Jan Aushadhi stores by pin code."""
        self.load()
        store_rows = self._stores_by_pin.get(pin_code, [])

        # Also check nearby pin codes (same first 3 digits = same area)
        if len(store_rows) < limit:
            prefix = pin_code[:3]
            for pin, stores in self._stores_by_pin.items():
                if pin.startswith(prefix) and pin != pin_code:
                    store_rows.extend(stores)
                    if len(store_rows) >= limit * 2:
                        break

        results = []
        seen = set()
        for s in store_rows[:limit]:
            code = s.get("store_code", "")
            if code in seen:
                continue
            seen.add(code)
            results.append(StoreResult(
                store_code=code,
                address=s.get("address", ""),
                district=s.get("district", ""),
                state=s.get("state", ""),
                pin_code=s.get("pin_code", ""),
                phone=s.get("phone", ""),
            ))

        return results


# Singleton — always uses CSV data (reliable for demo/production).
# Supabase can be enabled by setting FORCE_SUPABASE_LOOKUP=1 env var.
from app.core.config import settings

_drug_lookup_instance = None

def get_drug_lookup():
    global _drug_lookup_instance
    if _drug_lookup_instance is None:
        _drug_lookup_instance = DrugLookupService()
        _drug_lookup_instance.load()
    return _drug_lookup_instance

drug_lookup = get_drug_lookup()
