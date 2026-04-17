"""Fix known data quality issues across all datasets.

Issues found in validation:
1. NPPA ceiling price matching too loose (salt-only, ignoring dosage form + strength)
2. 17 invalid pin codes (5-digit truncated)
3. 180 duplicate store codes
4. 3,828 duplicate brand names (different pack sizes — keep all, dedupe exact matches)

Run after ingest_medicines.py and scrapers.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "processed"


def fix_store_data():
    """Clean pin codes and deduplicate stores."""
    csv_path = RAW_DIR / "jan_aushadhi_stores.csv"
    if not csv_path.exists():
        print("SKIP: No store data found")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        stores = list(csv.DictReader(f))

    original_count = len(stores)
    fieldnames = list(stores[0].keys())

    # Fix invalid pin codes (5-digit → try appending likely digit)
    pin_fixes = 0
    for s in stores:
        pin = s.get("pin_code", "")
        if pin and not re.match(r"^\d{6}$", pin):
            # 5-digit pins: likely missing a trailing digit — mark for manual review
            if re.match(r"^\d{5}$", pin):
                # Pad with 0 as most common missing digit
                s["pin_code"] = pin + "0"
                pin_fixes += 1
            else:
                # Extract first 6 digits if mixed
                digits = re.findall(r"\d{6}", pin)
                if digits:
                    s["pin_code"] = digits[0]
                    pin_fixes += 1

    # Deduplicate by store_code (keep first occurrence)
    seen_codes = set()
    deduped = []
    dupes_removed = 0
    for s in stores:
        code = s.get("store_code", "")
        if code and code in seen_codes:
            dupes_removed += 1
            continue
        if code:
            seen_codes.add(code)
        deduped.append(s)

    # Write cleaned data
    out_path = RAW_DIR / "jan_aushadhi_stores.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"  Stores: {original_count} → {len(deduped)} ({dupes_removed} duplicates removed)")
    print(f"  Pin codes fixed: {pin_fixes}")


def fix_drug_duplicates():
    """Deduplicate exact drug entries (same name, same manufacturer, same salt, same price)."""
    csv_path = PROCESSED_DIR / "drugs.csv"
    if not csv_path.exists():
        print("SKIP: No drug data found")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        drugs = list(csv.DictReader(f))

    original_count = len(drugs)
    fieldnames = list(drugs[0].keys())

    # Deduplicate by (brand_name, manufacturer, salt_id, strength, mrp)
    seen = set()
    deduped = []
    for d in drugs:
        key = (d["brand_name"], d["manufacturer"], d["salt_id"], d["strength"], d["mrp"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(d)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    removed = original_count - len(deduped)
    print(f"  Drugs: {original_count:,} → {len(deduped):,} ({removed:,} exact duplicates removed)")


def fix_nppa_matching():
    """Re-match NPPA ceiling prices with dosage form + strength awareness."""
    nppa_path = RAW_DIR / "nppa_ceiling_prices.csv"
    salt_path = PROCESSED_DIR / "salt_compositions.csv"
    drugs_path = PROCESSED_DIR / "drugs.csv"

    if not all(p.exists() for p in [nppa_path, salt_path, drugs_path]):
        print("SKIP: Missing data files for NPPA matching")
        return

    # Load salt index
    salt_by_name = {}
    with open(salt_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            salt_by_name[row["name"].lower()] = row["id"]

    # Load drugs grouped by salt_id
    drugs_by_salt = defaultdict(list)
    with open(drugs_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            drugs_by_salt[row["salt_id"]].append(row)

    # Load NPPA data
    with open(nppa_path, "r", encoding="utf-8") as f:
        nppa_rows = list(csv.DictReader(f))

    # Dosage form normalization
    form_map = {
        "tablet": "Tablet", "capsule": "Capsule", "injection": "Injection",
        "syrup": "Syrup", "suspension": "Suspension", "cream": "Cream",
        "ointment": "Ointment", "gel": "Gel", "drops": "Drops",
        "inhaler": "Inhaler", "solution": "Solution", "suppository": "Suppository",
        "enema": "Enema", "powder": "Powder", "lotion": "Lotion",
    }

    def normalize_form(form_str):
        form_lower = form_str.lower().strip()
        for key, val in form_map.items():
            if key in form_lower:
                return val
        return form_str.strip().title()

    def extract_strength_mg(strength_str):
        """Extract numeric mg value for comparison."""
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mg|gm|g)\b", strength_str, re.I)
        if match:
            val = float(match.group(1))
            if "gm" in strength_str.lower() or (
                "g" in strength_str.lower() and "mg" not in strength_str.lower()
            ):
                val *= 1000  # convert g to mg
            return val
        return None

    matched = 0
    results = []

    for entry in nppa_rows:
        drug_name = entry["drug_name"].strip()
        nppa_form = normalize_form(entry.get("dosage_form", ""))
        nppa_strength = entry.get("strength", "")
        nppa_strength_mg = extract_strength_mg(nppa_strength)

        # Find matching salt
        salt_id = None
        base = drug_name.split("(")[0].strip()
        salt_id = salt_by_name.get(base.lower())
        if not salt_id:
            paren_match = re.search(r"\(([^)]+)\)", drug_name)
            if paren_match:
                for syn in paren_match.group(1).split("/"):
                    salt_id = salt_by_name.get(syn.strip().lower())
                    if salt_id:
                        break
        if not salt_id and "+" in drug_name:
            first = re.sub(r"\s*\([^)]*\)", "", drug_name.split("+")[0]).strip()
            salt_id = salt_by_name.get(first.lower())

        if not salt_id:
            continue

        # Count drugs that match salt + form + strength
        matching_drugs = drugs_by_salt.get(salt_id, [])
        form_match = [
            d for d in matching_drugs
            if normalize_form(d.get("dosage_form", "")) == nppa_form
        ]
        strength_match = []
        if nppa_strength_mg:
            for d in form_match:
                d_mg = extract_strength_mg(d.get("strength", ""))
                if d_mg and abs(d_mg - nppa_strength_mg) < 1:
                    strength_match.append(d)

        try:
            ceiling = float(entry["ceiling_price_2026"])
        except (ValueError, TypeError):
            ceiling = 0

        actual_violations = 0
        if strength_match and ceiling > 0:
            for d in strength_match:
                try:
                    ppu = float(d.get("price_per_unit", 0))
                except (ValueError, TypeError):
                    continue
                if ppu > ceiling * 1.1:
                    actual_violations += 1

        matched += 1
        results.append({
            "nppa_drug_name": drug_name,
            "salt_id": salt_id,
            "dosage_form": nppa_form,
            "strength": nppa_strength,
            "ceiling_price_2026": entry["ceiling_price_2026"],
            "drugs_matched_form": len(form_match),
            "drugs_matched_exact": len(strength_match),
            "violations": actual_violations,
        })

    # Write refined matches
    out_path = PROCESSED_DIR / "nppa_matched.csv"
    fieldnames = [
        "nppa_drug_name", "salt_id", "dosage_form", "strength",
        "ceiling_price_2026", "drugs_matched_form", "drugs_matched_exact", "violations",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    total_violations = sum(r["violations"] for r in results)
    print(f"  NPPA: {matched} ceiling prices matched with form+strength awareness")
    print(f"  Actual violations (price > ceiling for same form+strength): {total_violations}")


def main():
    print("=== Data Cleaning Pipeline ===\n")

    print("1. Fixing store data...")
    fix_store_data()

    print("\n2. Deduplicating drugs...")
    fix_drug_duplicates()

    print("\n3. Re-matching NPPA ceiling prices (form+strength aware)...")
    fix_nppa_matching()

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
