"""Demonstrate the core product logic: given a branded drug, find cheapest generics.

Works entirely from the processed CSV files — no database or services needed.
This proves the data pipeline produces usable drug-to-generic mappings.

Usage:
  python data/processors/find_generics.py "Crocin"
  python data/processors/find_generics.py "Augmentin 625"
  python data/processors/find_generics.py "Azithromycin"
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "processed"


def load_data():
    """Load salt index and drugs from processed CSVs."""
    # Load salts: id → name
    salt_names = {}
    salt_by_name = {}
    with open(PROCESSED_DIR / "salt_compositions.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            salt_names[row["id"]] = row["name"]
            salt_by_name[row["name"].lower()] = row["id"]

    # Load drugs, grouped by salt_id
    drugs_by_salt = defaultdict(list)
    with open(PROCESSED_DIR / "drugs.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            drugs_by_salt[row["salt_id"]].append(row)

    return salt_names, salt_by_name, drugs_by_salt


def search_drug(query: str, salt_names, salt_by_name, drugs_by_salt):
    """Search for a drug by brand name or salt name and find generics."""
    query_lower = query.lower().strip()

    # Strategy 1: Exact salt name match
    matched_salt_id = salt_by_name.get(query_lower)

    # Strategy 2: Search brand names
    matching_drugs = []
    if not matched_salt_id:
        for salt_id, drugs in drugs_by_salt.items():
            for d in drugs:
                if query_lower in d["brand_name"].lower():
                    matching_drugs.append(d)
                    matched_salt_id = salt_id
                    break
            if matched_salt_id:
                break

    if not matched_salt_id:
        return None

    salt_name = salt_names.get(matched_salt_id, "Unknown")
    all_drugs = drugs_by_salt.get(matched_salt_id, [])

    if not all_drugs:
        return None

    # Find the branded drug (highest price match)
    brand_match = None
    if matching_drugs:
        brand_match = matching_drugs[0]
    else:
        # Use most expensive as the "branded" reference
        all_drugs_sorted = sorted(all_drugs, key=lambda d: float(d.get("mrp", 0)), reverse=True)
        brand_match = all_drugs_sorted[0]

    # Find generics: same salt, same strength, different (cheaper) products
    brand_strength = brand_match.get("strength", "")
    brand_form = brand_match.get("dosage_form", "")
    brand_mrp = float(brand_match.get("mrp", 0))

    generics = []
    for d in all_drugs:
        if d["id"] == brand_match["id"]:
            continue
        d_mrp = float(d.get("mrp", 0))
        if d_mrp < brand_mrp and d.get("strength") == brand_strength:
            generics.append(d)

    # Sort by price (cheapest first)
    generics.sort(key=lambda d: float(d.get("mrp", 0)))

    return {
        "brand": brand_match,
        "salt": salt_name,
        "strength": brand_strength,
        "dosage_form": brand_form,
        "generics": generics,
        "total_alternatives": len(generics),
    }


def format_result(result: dict) -> str:
    """Format search results as a WhatsApp-style message."""
    if not result:
        return "No match found."

    brand = result["brand"]
    brand_mrp = float(brand["mrp"])
    lines = [
        f"{'=' * 40}",
        f"  {brand['brand_name']}",
        f"  Salt: {result['salt']} {result['strength']}",
        f"  MRP: Rs.{brand_mrp:.2f} ({brand.get('pack_size', 'N/A')})",
        f"  Manufacturer: {brand['manufacturer']}",
        f"{'=' * 40}",
        "",
    ]

    if result["generics"]:
        cheapest = result["generics"][0]
        cheapest_mrp = float(cheapest["mrp"])
        savings = brand_mrp - cheapest_mrp
        savings_pct = (savings / brand_mrp * 100) if brand_mrp > 0 else 0

        lines.append(f"  CHEAPEST GENERIC:")
        lines.append(f"  {cheapest['brand_name']}")
        lines.append(f"  Price: Rs.{cheapest_mrp:.2f} ({cheapest.get('pack_size', 'N/A')})")
        lines.append(f"  Manufacturer: {cheapest['manufacturer']}")
        lines.append(f"  You save: Rs.{savings:.2f} ({savings_pct:.0f}%)")
        lines.append("")

        # Show top 5 alternatives
        top_n = min(5, len(result["generics"]))
        lines.append(f"  TOP {top_n} CHEAPEST (of {result['total_alternatives']} alternatives):")
        for i, g in enumerate(result["generics"][:top_n]):
            g_mrp = float(g["mrp"])
            lines.append(f"  {i+1}. {g['brand_name']} — Rs.{g_mrp:.2f} ({g['manufacturer']})")
    else:
        lines.append("  No cheaper alternatives found for this exact formulation.")

    lines.append("")
    lines.append("  Always consult your doctor before switching medicines.")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_generics.py <drug name>")
        print('Example: python find_generics.py "Crocin"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"Searching for: {query}\n")

    salt_names, salt_by_name, drugs_by_salt = load_data()
    result = search_drug(query, salt_names, salt_by_name, drugs_by_salt)
    print(format_result(result))


if __name__ == "__main__":
    main()
