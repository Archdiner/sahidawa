"""Cross-reference NPPA ceiling prices with the drug database.

Maps NPPA molecule names to our salt composition index so we can show:
"Government ceiling price for this drug is Rs.X" alongside generic alternatives.

This helps users understand not just the cheapest generic but also the
legal maximum price for regulated drugs.

Usage:
  python data/processors/integrate_nppa.py
"""

import csv
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
RAW_DIR = Path(__file__).parent.parent / "raw"


def load_salt_index() -> dict[str, str]:
    """Load salt name → id mapping."""
    index = {}
    with open(PROCESSED_DIR / "salt_compositions.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            index[row["name"].lower()] = row["id"]
    return index


def match_nppa_to_salts():
    """Match NPPA drug names to our salt composition index."""
    nppa_path = RAW_DIR / "nppa_ceiling_prices.csv"
    if not nppa_path.exists():
        print("ERROR: NPPA data not found. Run scrapers/nppa.py first.")
        return

    salt_index = load_salt_index()
    print(f"Loaded {len(salt_index)} salts from our index")

    with open(nppa_path, "r", encoding="utf-8") as f:
        nppa_rows = list(csv.DictReader(f))

    print(f"NPPA entries: {len(nppa_rows)}")

    matched = 0
    unmatched = []
    results = []

    for row in nppa_rows:
        drug_name = row["drug_name"].strip()

        # Try direct match
        salt_id = salt_index.get(drug_name.lower())

        # Try common transformations
        if not salt_id:
            # Strip parenthetical synonyms: "5-amino salicylic Acid (Mesalazine/Mesalamine)"
            base = drug_name.split("(")[0].strip()
            salt_id = salt_index.get(base.lower())

        if not salt_id:
            # Try the synonym in parens
            import re
            paren_match = re.search(r"\(([^)]+)\)", drug_name)
            if paren_match:
                for syn in paren_match.group(1).split("/"):
                    salt_id = salt_index.get(syn.strip().lower())
                    if salt_id:
                        break

        if not salt_id:
            # Try title case
            salt_id = salt_index.get(drug_name.title().lower())

        # For combination drugs: "Abacavir (A) +Lamivudine(B)"
        if not salt_id and "+" in drug_name:
            first_salt = drug_name.split("+")[0].strip()
            first_salt = re.sub(r"\s*\([^)]*\)", "", first_salt).strip()
            salt_id = salt_index.get(first_salt.lower())

        if salt_id:
            matched += 1
            results.append({
                "nppa_drug_name": drug_name,
                "salt_id": salt_id,
                "dosage_form": row["dosage_form"],
                "strength": row["strength"],
                "unit": row["unit"],
                "ceiling_price_2026": row["ceiling_price_2026"],
            })
        else:
            unmatched.append(drug_name)

    # Write matched results
    out_path = PROCESSED_DIR / "nppa_matched.csv"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["nppa_drug_name", "salt_id", "dosage_form", "strength", "unit", "ceiling_price_2026"],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nMatched: {matched}/{len(nppa_rows)} ({matched/len(nppa_rows)*100:.1f}%)")
    print(f"Saved to: {out_path}")

    if unmatched:
        print(f"\nUnmatched NPPA drugs ({len(unmatched)}):")
        for name in unmatched[:20]:
            print(f"  - {name}")
        if len(unmatched) > 20:
            print(f"  ... and {len(unmatched) - 20} more")


if __name__ == "__main__":
    match_nppa_to_salts()
