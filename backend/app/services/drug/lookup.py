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
# project root = 5 parents up
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
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

    def search(self, query: str) -> list[dict]:
        """Search for drugs matching the query string.

        Returns results scored by relevance:
        - Exact full name match scores highest
        - First-word match next
        - Substring/salt match last
        """
        self.load()
        query_lower = query.lower().strip()
        query_words = query_lower.split()

        scored: list[tuple[int, dict]] = []

        # Strategy 1: Exact brand name match (highest score)
        if query_lower in self._brand_index:
            for d in self._brand_index[query_lower]:
                scored.append((100, d))

        # Strategy 2: First word match
        if not scored and query_words:
            first = query_words[0]
            if first in self._brand_index:
                for d in self._brand_index[first]:
                    # Bonus if more words match
                    name_lower = d["brand_name"].lower()
                    word_matches = sum(1 for w in query_words if w in name_lower)
                    scored.append((50 + word_matches * 10, d))

        # Strategy 3: Salt name match (good for single-word generic queries like "Pantoprazole")
        salt_id = self._salt_by_name.get(query_lower)
        if salt_id and not scored:
            for d in self._drugs_by_salt.get(salt_id, []):
                scored.append((80, d))

        # Strategy 4: Substring match (lower score)
        if not scored:
            for name, drugs in self._brand_index.items():
                if query_lower in name or any(w in name for w in query_words):
                    for d in drugs:
                        scored.append((20, d))
                    if len(scored) > 50:
                        break

        # Strategy 5: Salt name partial match
        if not scored:
            salt_id = self._salt_by_name.get(query_lower)
            if salt_id:
                for d in self._drugs_by_salt.get(salt_id, []):
                    scored.append((10, d))

        # Sort by score (descending), then by price (descending for branded reference)
        scored.sort(key=lambda x: (x[0], float(x[1].get("mrp", 0))), reverse=True)
        return [d for _, d in scored[:100]]

    def _pick_best_match(self, query: str, hits: list[dict]) -> dict:
        """Pick the single best branded drug match from search hits.

        Prefers: exact name match > name contains query > highest price.
        Among ties, picks the popular branded version (higher price).
        """
        query_lower = query.lower().strip()
        query_words = query_lower.split()

        # Extract strength hint from query (e.g., "500" from "Crocin 500")
        strength_hint = ""
        for w in query_words:
            if re.match(r"\d+", w):
                strength_hint = w
                break

        best = None
        best_score = -1

        for d in hits:
            name_lower = d["brand_name"].lower()
            score = 0

            # Exact full name match
            if name_lower == query_lower:
                score += 1000

            # Name starts with query
            if name_lower.startswith(query_words[0]):
                score += 100

            # All query words present in name
            word_matches = sum(1 for w in query_words if w in name_lower)
            score += word_matches * 20

            # Strength match bonus
            if strength_hint and strength_hint in d.get("strength", ""):
                score += 50

            # Prefer tablets over injections/infusions (more common user request)
            form = d.get("dosage_form", "").lower()
            if "tablet" in form:
                score += 10
            elif "capsule" in form:
                score += 8
            elif "syrup" in form:
                score += 5

            # Tiebreaker: higher price = more likely the branded version
            score += float(d.get("mrp", 0)) / 10000

            if score > best_score:
                best_score = score
                best = d

        return best or hits[0]

    def lookup(self, query: str, pin_code: str | None = None) -> LookupResult:
        """Full lookup: find drug, generics, ceiling price, and nearby stores."""
        self.load()

        hits = self.search(query)
        if not hits:
            return LookupResult(query=query, matched=False)

        # Pick the best match using smart ranking
        top = self._pick_best_match(query, hits)

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

        # Nearby stores by pin code
        stores = []
        if pin_code:
            store_rows = self._stores_by_pin.get(pin_code, [])
            for s in store_rows[:5]:
                stores.append(StoreResult(
                    store_code=s.get("store_code", ""),
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


# Singleton for the app
drug_lookup = DrugLookupService()
