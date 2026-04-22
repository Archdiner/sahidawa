#!/usr/bin/env python3
"""Batch geocode Jan Aushadhi stores via Google Maps API — with PIN fallback.

Approach:
1. Address-based geocoding (address + ", India")
2. For stores that fail: PIN-only fallback (PIN + ", India")

This recovers the ~2100 stores where address text didn't match but PIN is correct.

Usage:
    python geocode_stores_v2.py --dry-run        # test 5 stores
    python geocode_stores_v2.py --failed-only   # re-geocode only the 2113 NULL stores
    python geocode_stores_v2.py                  # full re-geocode all stores
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

BATCH_SIZE = 50
CONCURRENT_REQUESTS = 10
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
SOURCE_CSV = "../data/raw/jan_aushadhi_stores.csv"
SEMAPHORE_LIMIT = 10

_gc_params = {"key": settings.google_maps_api_key}


async def geocode_address(address: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> dict | None:
    async with semaphore:
        try:
            resp = await client.get(
                GEOCODING_URL,
                params={**_gc_params, "address": f"{address}, India"},
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


async def geocode_pin(pin: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> dict | None:
    async with semaphore:
        try:
            resp = await client.get(
                GEOCODING_URL,
                params={**_gc_params, "address": f"{pin}, India"},
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
    parser.add_argument("--dry-run", action="store_true", help="Test 5 stores only")
    parser.add_argument("--failed-only", action="store_true", help="Only re-geocode NULL stores")
    args = parser.parse_args()

    key = settings.supabase_secret_key
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    base = settings.supabase_url

    # Load store metadata from CSV (preserves original address order)
    stores_by_code = {}
    with open(SOURCE_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stores_by_code[row["store_code"]] = row

    # Fetch current state from Supabase
    print("Fetching current state from Supabase...")
    all_stores = []
    offset = 0
    while True:
        resp = httpx.get(
            f"{base}/rest/v1/jan_aushadhi_stores?select=store_code,latitude,longitude&offset={offset}&limit=1000",
            headers=headers,
            timeout=30,
        )
        data = resp.json()
        if not data:
            break
        all_stores.extend(data)
        offset += 1000
        if len(data) < 1000:
            break

    if args.dry_run:
        all_stores = all_stores[:5]
        print(f"[DRY RUN] Testing {len(all_stores)} stores...")

    # Determine which need geocoding
    need_geocode = [s for s in all_stores if s.get("latitude") is None]
    already_geocoded = [s for s in all_stores if s.get("latitude") is not None]

    print(f"Already geocoded: {len(already_geocoded)}")
    print(f"Need geocoding: {len(need_geocode)}")

    if args.dry_run:
        need_geocode = need_geocode[:5]

    if not need_geocode:
        print("Nothing to geocode!")
        return

    # Two-phase geocoding: address first, then PIN fallback
    results = {}  # store_code -> {"lat": ..., "lng": ..., "method": "address"|"pin"}
    phase1_fail_count = 0

    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    t0 = time.time()

    print("\n=== Phase 1: Address-based geocoding ===")
    async with httpx.AsyncClient() as client:
        for i in range(0, len(need_geocode), BATCH_SIZE):
            batch = need_geocode[i:i + BATCH_SIZE]
            tasks = [geocode_address(stores_by_code[s["store_code"]]["address"], client, semaphore) for s in batch]
            resolved = await asyncio.gather(*tasks)
            for s, geo in zip(batch, resolved):
                if geo:
                    results[s["store_code"]] = {**geo, "method": "address"}
                else:
                    phase1_fail_count += 1

            done = min(i + BATCH_SIZE, len(need_geocode))
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            addr_success = sum(1 for code in results if results[code]["method"] == "address")
            print(f"  [{done}/{len(need_geocode)}] addr_success={addr_success}, phase1_failed={phase1_fail_count}, {rate:.1f} addr/s")

    print(f"\nPhase 1 complete: {len([r for r in results.values() if r['method']=='address'])} by address, {phase1_fail_count} need PIN fallback")

    # Phase 2: PIN-only fallback for remaining
    phase2_fail_count = 0
    failed_codes = [s["store_code"] for s in need_geocode if s["store_code"] not in results]

    print(f"\n=== Phase 2: PIN-only fallback for {len(failed_codes)} stores ===")
    t1 = time.time()

    semaphore2 = asyncio.Semaphore(SEMAPHORE_LIMIT)
    async with httpx.AsyncClient() as client:
        for i in range(0, len(failed_codes), BATCH_SIZE):
            batch_codes = failed_codes[i:i + BATCH_SIZE]
            batch_pins = [stores_by_code[c]["pin_code"] for c in batch_codes]
            tasks = [geocode_pin(pin, client, semaphore2) for pin in batch_pins]
            resolved = await asyncio.gather(*tasks)
            for code, geo in zip(batch_codes, resolved):
                if geo:
                    results[code] = {**geo, "method": "pin"}
                else:
                    phase2_fail_count += 1

            done = min(i + BATCH_SIZE, len(failed_codes))
            elapsed = time.time() - t1
            rate = done / elapsed if elapsed > 0 else 0
            pin_success = sum(1 for code in results if results[code]["method"] == "pin")
            print(f"  [{done}/{len(failed_codes)}] pin_success={pin_success}, still_failed={phase2_fail_count}, {rate:.1f} pin/s")

    print(f"\n=== GEOCODING SUMMARY ===")
    addr_by_addr = sum(1 for r in results.values() if r["method"] == "address")
    addr_by_pin = sum(1 for r in results.values() if r["method"] == "pin")
    total_recovered = addr_by_addr + addr_by_pin
    total_failed = phase1_fail_count + phase2_fail_count - addr_by_pin  # phase2 fails already counted in phase1 fail
    print(f"  Address-based:   {addr_by_addr}")
    print(f"  PIN-based:      {addr_by_pin}")
    print(f"  Unrecovered:    {phase2_fail_count}")
    print(f"  Total recovered: {total_recovered}/{len(need_geocode)} ({100*total_recovered/len(need_geocode):.1f}%)")

    if not results:
        print("No results to update.")
        return

    if args.dry_run:
        print("\n[DRY RUN] Skipping Supabase update.")
        for code, geo in list(results.items())[:5]:
            print(f"  {code}: {geo}")
        return

    # Update Supabase
    print("\nUpdating Supabase...")
    t2 = time.time()

    async def do_update(code: str, lat: float, lng: float):
        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            resp = await client.patch(
                f"{base}/rest/v1/jan_aushadhi_stores",
                params={"store_code": f"eq.{code}"},
                json={"latitude": lat, "longitude": lng},
            )
            return code, resp.status_code

    semaphore3 = asyncio.Semaphore(5)
    tasks = [do_update(code, geo["lat"], geo["lng"]) for code, geo in results.items()]
    update_results = await asyncio.gather(*tasks, return_exceptions=True)

    succeeded = sum(1 for r in update_results if not isinstance(r, Exception) and r[1] in (200, 201, 206))
    failed_update = len(update_results) - succeeded

    print(f"Supabase update: {succeeded} succeeded, {failed_update} failed in {time.time()-t2:.1f}s")

    # Final summary
    total_stores = len(all_stores)
    total_geocoded = len(already_geocoded) + len(results)
    print(f"\nFinal: {total_geocoded}/{total_stores} stores geocoded ({100*total_geocoded/total_stores:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())