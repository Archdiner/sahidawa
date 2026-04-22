#!/usr/bin/env python3
"""Batch geocode Jan Aushadhi stores via Google Maps API.

Uses address geocoding (no lat/lng in source) to populate
latitude/longitude columns in Supabase.

Usage:
    python geocode_stores.py --dry-run  # test 5 stores
    python geocode_stores.py            # geocode all stores

Rate limit: 50 req/s for Geocoding API. We use 10 req/s with async
to stay well within quota while maximizing throughput.
"""

import argparse
import asyncio
import csv
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent / "backend"))
from app.core.config import settings

BATCH_SIZE = 50          # stores per API batch
CONCURRENT_REQUESTS = 10  # requests per second (API limit is 50/s)
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
SOURCE_CSV = "../data/raw/jan_aushadhi_stores.csv"
SEMAPHORE_LIMIT = 10


async def geocode_address(address: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> dict | None:
    """Geocode a single address string. Returns (lat, lng) or None."""
    async with semaphore:
        try:
            resp = await client.get(
                GEOCODING_URL,
                params={
                    "address": f"{address}, India",
                    "key": settings.google_maps_api_key,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    loc = results[0]["geometry"]["location"]
                    return {"lat": loc["lat"], "lng": loc["lng"]}
            return None
        except Exception:
            return None


async def main():
    parser = argparse.ArgumentParser(description="Geocode Jan Aushadhi stores")
    parser.add_argument("--dry-run", action="store_true", help="Geocode only first 5 stores")
    args = parser.parse_args()

    # Load stores
    stores = []
    with open(SOURCE_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stores.append(row)

    if args.dry_run:
        stores = stores[:5]
        print(f"[DRY RUN] Testing {len(stores)} stores...")
    else:
        print(f"Geocoding {len(stores)} stores...")

    # Check which stores already have coordinates
    existing = 0
    for s in stores:
        if s.get("latitude") and s.get("longitude"):
            existing += 1
    print(f"  Already geocoded: {existing}")

    # Build work list
    to_geocode = [s for s in stores if not s.get("latitude")]
    print(f"  Need to geocode: {len(to_geocode)}")

    if not to_geocode:
        print("All stores already geocoded!")
        return

    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    results = {}  # store_code -> {"lat": ..., "lng": ...}

    async with httpx.AsyncClient() as client:
        t0 = time.time()
        for i in range(0, len(to_geocode), BATCH_SIZE):
            batch = to_geocode[i:i + BATCH_SIZE]
            tasks = [
                geocode_address(s["address"], client, semaphore)
                for s in batch
            ]
            resolved = await asyncio.gather(*tasks)
            for s, geo in zip(batch, resolved):
                if geo:
                    results[s["store_code"]] = geo

            elapsed = time.time() - t0
            done = min(i + BATCH_SIZE, len(to_geocode))
            rate = done / elapsed if elapsed > 0 else 0
            print(f"  [{done}/{len(to_geocode)}] {elapsed:.1f}s elapsed, {rate:.1f} addr/s")

    print(f"\nGeocoded: {len(results)}/{len(to_geocode)}")
    if args.dry_run:
        for code, geo in list(results.items())[:5]:
            print(f"  {code}: {geo}")
        return

    # Update Supabase
    print("\nUpdating Supabase...")
    key = settings.supabase_secret_key
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    base = settings.supabase_url

    async def update_store(code: str, lat: float, lng: float):
        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            resp = await client.patch(
                f"{base}/rest/v1/jan_aushadhi_stores",
                params={"store_code": f"eq.{code}"},
                json={"latitude": lat, "longitude": lng},
            )
            return code, resp.status_code

    semaphore2 = asyncio.Semaphore(5)
    updates = []

    async def do_update(code: str, lat: float, lng: float):
        async with semaphore2:
            async with httpx.AsyncClient(headers=headers, timeout=15) as client:
                resp = await client.patch(
                    f"{base}/rest/v1/jan_aushadhi_stores",
                    params={"store_code": f"eq.{code}"},
                    json={"latitude": lat, "longitude": lng},
                )
                return code, resp.status_code

    t1 = time.time()
    tasks = [do_update(code, geo["lat"], geo["lng"]) for code, geo in results.items()]
    update_results = await asyncio.gather(*tasks, return_exceptions=True)

    succeeded = sum(1 for r in update_results if not isinstance(r, Exception) and r[1] in (200, 201, 206))
    failed = len(update_results) - succeeded

    print(f"Supabase update: {succeeded} succeeded, {failed} failed in {time.time()-t1:.1f}s")

    # Summary
    total = len(stores)
    geocoded = existing + len(results)
    print(f"\nTotal stores: {total}, geocoded: {geocoded} ({100*geocoded/total:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())