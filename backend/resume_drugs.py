#!/usr/bin/env python3
"""Resume drug migration — only inserts missing records (idempotent)."""

import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))
from app.core.config import settings
import httpx

BATCH = 200
SOURCE = "../data/processed/drugs.csv"

def get_existing_ids():
    """Fetch all existing drug IDs from Supabase."""
    key = settings.supabase_secret_key
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    existing = set()
    offset = 0
    while True:
        resp = httpx.get(
            f"{settings.supabase_url}/rest/v1/drugs?select=id",
            headers=headers,
            params={"offset": offset, "limit": 1000},
            timeout=30,
        )
        data = resp.json()
        if not data:
            break
        existing.update(r["id"] for r in data)
        offset += 1000
        if len(data) < 1000:
            break
    return existing

def main():
    print("Fetching existing drug IDs...")
    existing = get_existing_ids()
    print(f"Already have {len(existing)} drugs in DB")

    print(f"Loading CSV...")
    records = []
    with open(SOURCE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] not in existing:
                records.append({
                    "id": row["id"],
                    "brand_name": row["brand_name"],
                    "manufacturer": row["manufacturer"],
                    "salt_id": row["salt_id"],
                    "strength": row["strength"],
                    "dosage_form": row["dosage_form"],
                    "pack_size": row.get("pack_size") or None,
                    "mrp": float(row["mrp"]),
                    "price_per_unit": float(row["price_per_unit"]) if row.get("price_per_unit") else None,
                    "source": row.get("source") or None,
                })

    print(f"Need to insert {len(records)} new drugs (skipping {245987 - len(records)} already existing)")

    key = settings.supabase_secret_key
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    inserted = 0
    errors = 0
    for i in range(0, len(records), BATCH):
        batch = records[i:i + BATCH]
        try:
            resp = httpx.post(
                f"{settings.supabase_url}/rest/v1/drugs",
                headers=headers,
                json=batch,
                timeout=60,
            )
            if resp.status_code in (200, 201):
                inserted += len(batch)
            else:
                # Try one by one
                for rec in batch:
                    try:
                        r2 = httpx.post(
                            f"{settings.supabase_url}/rest/v1/drugs",
                            headers=headers,
                            json=[rec],
                            timeout=30,
                        )
                        if r2.status_code in (200, 201):
                            inserted += 1
                    except Exception:
                        errors += 1
        except Exception as e:
            errors += len(batch)

        print(f"  Progress: {inserted}/{len(records)} inserted ({errors} errors)")

    print(f"\nDone! Inserted {inserted} drugs, {errors} errors")


if __name__ == "__main__":
    main()