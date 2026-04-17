"""Ingest the Indian Medicine Dataset CSV into PostgreSQL.

Pipeline:
1. Read the 253K-row CSV (name, price, manufacturer, pack_size, composition1, composition2)
2. Extract and normalize unique salt compositions
3. Create SaltComposition records
4. Create Drug records linked to their salt compositions
5. Index everything into Meilisearch for fuzzy search

The composition field looks like: "Amoxycillin  (500mg) " or "Paracetamol (500mg)"
We need to extract: salt name, strength, and normalize spelling variants.
"""

import csv
import re
import sys
import uuid
from pathlib import Path

# Add backend to path for model imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


def parse_composition(comp_str: str) -> tuple[str, str]:
    """Parse 'Amoxycillin  (500mg)' → ('Amoxycillin', '500mg').

    Returns (salt_name, strength).
    """
    if not comp_str or not comp_str.strip():
        return ("", "")

    comp_str = comp_str.strip()
    # Match: name (strength) or name (strength/unit)
    match = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", comp_str)
    if match:
        name = match.group(1).strip()
        strength = match.group(2).strip()
        return (name, strength)

    # No parenthetical strength — just a name
    return (comp_str.strip(), "")


def normalize_salt_name(name: str) -> str:
    """Normalize salt name for consistent matching.

    - Strip extra spaces
    - Title case
    - Common synonym mapping
    """
    name = " ".join(name.split())  # collapse whitespace
    name = name.strip()

    # Common normalizations (lowercase → canonical)
    SYNONYMS = {
        "acetaminophen": "Paracetamol",
        "pcm": "Paracetamol",
        "paracetamol ip": "Paracetamol",
        "amoxycillin": "Amoxicillin",
        "amoxicillin": "Amoxicillin",
        "cephalexin": "Cefalexin",
        "erythromycin": "Erythromycin",
        "sulphamethoxazole": "Sulfamethoxazole",
        "metformin hcl": "Metformin",
        "metformin hydrochloride": "Metformin",
        "atorvastatin calcium": "Atorvastatin",
        "amlodipine besylate": "Amlodipine",
        "amlodipine besilate": "Amlodipine",
        "losartan potassium": "Losartan",
        "omeprazole magnesium": "Omeprazole",
        "pantoprazole sodium": "Pantoprazole",
        "rabeprazole sodium": "Rabeprazole",
        "clopidogrel bisulphate": "Clopidogrel",
        "clopidogrel bisulfate": "Clopidogrel",
    }

    lower = name.lower()
    if lower in SYNONYMS:
        return SYNONYMS[lower]

    # Default: title case
    return name.title() if name.islower() or name.isupper() else name


def parse_pack_size(label: str) -> tuple[str, str]:
    """Parse 'strip of 10 tablets' → ('strip of 10', 'tablet').

    Returns (pack_size, dosage_form).
    """
    if not label:
        return ("", "")

    label = label.strip().lower()

    # Common patterns
    form_map = {
        "tablet": "Tablet",
        "capsule": "Capsule",
        "syrup": "Syrup",
        "injection": "Injection",
        "cream": "Cream",
        "ointment": "Ointment",
        "gel": "Gel",
        "drops": "Drops",
        "suspension": "Suspension",
        "inhaler": "Inhaler",
        "solution": "Solution",
        "powder": "Powder",
        "lotion": "Lotion",
        "spray": "Spray",
        "patch": "Patch",
        "suppository": "Suppository",
        "respule": "Respule",
        "sachet": "Sachet",
        "soap": "Soap",
        "shampoo": "Shampoo",
    }

    dosage_form = ""
    for key, val in form_map.items():
        if key in label:
            dosage_form = val
            break

    # Extract quantity: "strip of 10" or "bottle of 100 ml"
    qty_match = re.search(r"(?:strip|bottle|pack|box|tube|vial|bag|jar)\s+of\s+(\d+\s*\w*)", label)
    pack_size = qty_match.group(0) if qty_match else label

    return (pack_size, dosage_form)


def load_csv(csv_path: str) -> list[dict]:
    """Load and parse the Indian Medicine Dataset CSV."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Is_discontinued") == "TRUE":
                continue  # skip discontinued

            price_str = row.get("price(₹)", "0")
            try:
                price = float(price_str) if price_str else 0.0
            except ValueError:
                price = 0.0

            if price <= 0:
                continue  # skip zero-price entries

            salt1_name, salt1_strength = parse_composition(row.get("short_composition1", ""))
            salt2_name, salt2_strength = parse_composition(row.get("short_composition2", ""))

            if not salt1_name:
                continue  # skip entries with no composition

            salt1_name = normalize_salt_name(salt1_name)
            if salt2_name:
                salt2_name = normalize_salt_name(salt2_name)

            # Build full composition string
            composition = salt1_name
            if salt1_strength:
                composition += f" {salt1_strength}"
            if salt2_name:
                composition += f" + {salt2_name}"
                if salt2_strength:
                    composition += f" {salt2_strength}"

            pack_size, dosage_form = parse_pack_size(row.get("pack_size_label", ""))

            records.append({
                "brand_name": row.get("name", "").strip(),
                "manufacturer": row.get("manufacturer_name", "").strip(),
                "salt_composition": composition,
                "primary_salt": salt1_name,
                "primary_strength": salt1_strength,
                "secondary_salt": salt2_name,
                "secondary_strength": salt2_strength,
                "mrp": price,
                "pack_size": pack_size,
                "dosage_form": dosage_form or "Unknown",
                "type": row.get("type", "allopathy"),
            })

    return records


def build_salt_index(records: list[dict]) -> dict[str, dict]:
    """Build a deduplicated index of unique salt compositions."""
    salt_index = {}  # normalized_name → {id, name, synonyms}

    for rec in records:
        key = rec["primary_salt"].lower()
        if key not in salt_index:
            salt_index[key] = {
                "id": str(uuid.uuid4()),
                "name": rec["primary_salt"],
                "synonyms": set(),
            }
        # Track original composition variants as synonyms
        salt_index[key]["synonyms"].add(rec["salt_composition"])

        if rec["secondary_salt"]:
            key2 = rec["secondary_salt"].lower()
            if key2 not in salt_index:
                salt_index[key2] = {
                    "id": str(uuid.uuid4()),
                    "name": rec["secondary_salt"],
                    "synonyms": set(),
                }

    # Convert synonym sets to lists
    for entry in salt_index.values():
        entry["synonyms"] = list(entry["synonyms"])[:20]  # cap at 20

    return salt_index


def export_for_db(records: list[dict], salt_index: dict, output_dir: str | None = None):
    """Export processed data as CSVs ready for PostgreSQL COPY import."""
    out = Path(output_dir) if output_dir else Path(__file__).parent.parent / "processed"
    out.mkdir(parents=True, exist_ok=True)

    # 1. Salt compositions CSV
    salt_path = out / "salt_compositions.csv"
    with open(salt_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "synonyms"])
        writer.writeheader()
        for entry in salt_index.values():
            writer.writerow({
                "id": entry["id"],
                "name": entry["name"],
                "synonyms": "|".join(entry["synonyms"]),
            })
    print(f"  Salt compositions: {len(salt_index)} → {salt_path}")

    # 2. Drugs CSV
    drugs_path = out / "drugs.csv"
    with open(drugs_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id", "brand_name", "manufacturer", "salt_id", "strength",
                "dosage_form", "pack_size", "mrp", "price_per_unit",
            ],
        )
        writer.writeheader()
        for rec in records:
            salt_key = rec["primary_salt"].lower()
            salt_id = salt_index.get(salt_key, {}).get("id", "")

            # Calculate price per unit
            qty_match = re.search(r"of\s+(\d+)", rec.get("pack_size", ""))
            qty = int(qty_match.group(1)) if qty_match else 1
            ppu = round(rec["mrp"] / qty, 4) if qty > 0 else rec["mrp"]

            writer.writerow({
                "id": str(uuid.uuid4()),
                "brand_name": rec["brand_name"],
                "manufacturer": rec["manufacturer"],
                "salt_id": salt_id,
                "strength": rec["primary_strength"],
                "dosage_form": rec["dosage_form"],
                "pack_size": rec["pack_size"],
                "mrp": rec["mrp"],
                "price_per_unit": ppu,
            })
    print(f"  Drugs: {len(records)} → {drugs_path}")

    # 3. Meilisearch documents JSON (for indexing)
    import json

    meili_path = out / "meili_drugs.jsonl"
    with open(meili_path, "w", encoding="utf-8") as f:
        for i, rec in enumerate(records):
            salt_key = rec["primary_salt"].lower()
            salt_id = salt_index.get(salt_key, {}).get("id", "")
            synonyms = salt_index.get(salt_key, {}).get("synonyms", [])

            qty_match = re.search(r"of\s+(\d+)", rec.get("pack_size", ""))
            qty = int(qty_match.group(1)) if qty_match else 1
            ppu = round(rec["mrp"] / qty, 4) if qty > 0 else rec["mrp"]

            doc = {
                "id": i,
                "brand_name": rec["brand_name"],
                "manufacturer": rec["manufacturer"],
                "salt_composition": rec["salt_composition"],
                "salt_id": salt_id,
                "salt_synonyms": " ".join(synonyms[:5]),
                "strength": rec["primary_strength"],
                "dosage_form": rec["dosage_form"],
                "pack_size": rec["pack_size"],
                "mrp": rec["mrp"],
                "price_per_unit": ppu,
                "is_generic": _is_likely_generic(rec),
            }
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(f"  Meilisearch docs: {len(records)} → {meili_path}")


def _is_likely_generic(rec: dict) -> bool:
    """Heuristic: a drug is likely a generic if its brand name closely matches
    its primary salt name, or if it's from a known generic manufacturer."""
    brand = rec["brand_name"].lower()
    salt = rec["primary_salt"].lower()

    # If brand name starts with the salt name, likely generic
    if brand.startswith(salt[:5]):
        return True

    # Known generic indicators in brand name
    generic_indicators = [" ip ", " bp ", "generic", " gp "]
    if any(ind in f" {brand} " for ind in generic_indicators):
        return True

    return False


def run(csv_path: str | None = None):
    """Full pipeline: CSV → parse → normalize → export."""
    csv_file = csv_path or str(Path(__file__).parent.parent / "raw" / "indian_medicines.csv")
    print(f"Loading CSV: {csv_file}")
    records = load_csv(csv_file)
    print(f"Loaded {len(records)} active drug records")

    print("Building salt composition index...")
    salt_index = build_salt_index(records)
    print(f"Found {len(salt_index)} unique salt compositions")

    print("Exporting processed data...")
    export_for_db(records, salt_index)

    # Summary stats
    manufacturers = set(r["manufacturer"] for r in records)
    dosage_forms = set(r["dosage_form"] for r in records)
    print(f"\nSummary:")
    print(f"  Active drugs: {len(records):,}")
    print(f"  Unique salts: {len(salt_index):,}")
    print(f"  Manufacturers: {len(manufacturers):,}")
    print(f"  Dosage forms: {len(dosage_forms)}")

    # Show top 10 most common salts
    from collections import Counter
    salt_counts = Counter(r["primary_salt"] for r in records)
    print(f"\nTop 20 most common salts:")
    for salt, count in salt_counts.most_common(20):
        print(f"  {salt}: {count:,} products")


if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    run(csv_path)
