#!/usr/bin/env python3
"""Concurrent drug migrator — resumes from existing data, skips duplicates."""

import asyncio
import csv
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent / "backend"))
from app.core.config import settings

BATCH_SIZE = 400
CONCURRENT_REQUESTS = 6
SOURCE = "../data/processed/drugs.csv"


async def main():
    key = settings.supabase_secret_key
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    base_url = settings.supabase_url

    # Fetch existing IDs
    print("Fetching existing drug IDs...")
    t0 = time.time()
    existing = set()
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        offset = 0
        while True:
            resp = await client.get(
                f"{base_url}/rest/v1/drugs?select=id",
                params={"offset": offset, "limit": 1000},
            )
            data = resp.json()
            if not data:
                break
            existing.update(r["id"] for r in data)
            offset += 1000
            if len(data) < 1000:
                break
    print(f"  Found {len(existing)} existing in {time.time()-t0:.1f}s")

    # Load CSV and filter
    print("Loading CSV...")
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
    print(f"  New records to insert: {len(records)}")

    if not records:
        print("All drugs already migrated!")
        return

    # Insert with controlled concurrency
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    inserted = 0
    failed = 0
    lock = asyncio.Lock()

    async def insert_one_batch(batch):
        nonlocal inserted, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient(headers=headers, timeout=60) as client:
                    resp = await client.post(
                        f"{base_url}/rest/v1/drugs",
                        json=batch,
                    )
                    if resp.status_code in (200, 201):
                        async with lock:
                            inserted += len(batch)
                            if inserted % 5000 == 0:
                                print(f"  Inserted: {inserted}/{len(records)}")
                    else:
                        async with lock:
                            failed += len(batch)
            except Exception as e:
                async with lock:
                    failed += len(batch)

    batches = [records[i:i + BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]
    print(f"Inserting {len(batches)} batches, {CONCURRENT_REQUESTS} concurrent...")
    t1 = time.time()

    await asyncio.gather(*[insert_one_batch(b) for b in batches])

    elapsed = time.time() - t1
    rate = inserted / elapsed if elapsed > 0 else 0
    print(f"\nDone in {elapsed:.1f}s ({rate:.0f} records/sec)")
    print(f"Inserted: {inserted}, Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())