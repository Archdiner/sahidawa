"""Geocode Jan Aushadhi store addresses to lat/lng coordinates.

Uses Google Maps Geocoding API to convert store addresses into
geographic coordinates for PostGIS nearest-store queries.

Writes results back to the stores CSV with lat/lng columns added.
Also updates PostgreSQL with the coordinates via PostGIS geometry.

Prerequisites:
  - GOOGLE_MAPS_API_KEY set in .env
  - Jan Aushadhi stores scraped (data/raw/jan_aushadhi_stores.csv)

Usage:
  python data/processors/geocode.py
"""

import asyncio
import csv
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

RAW_DIR = Path(__file__).parent.parent / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "processed"
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
RATE_LIMIT_DELAY = 0.05  # 20 requests/sec within free tier


async def geocode_address(client: httpx.AsyncClient, address: str, pin_code: str, state: str) -> tuple[float, float] | None:
    """Geocode a single address. Returns (lat, lng) or None."""
    # Build a reasonable search string
    query = f"{address}, {state}, India"
    if pin_code:
        query += f" {pin_code}"

    try:
        resp = await client.get(
            GEOCODE_URL,
            params={"address": query, "key": GOOGLE_API_KEY, "region": "in"},
        )
        data = resp.json()
        if data["status"] == "OK" and data["results"]:
            loc = data["results"][0]["geometry"]["location"]
            return (loc["lat"], loc["lng"])
    except Exception as e:
        print(f"  Geocode error for '{query[:50]}': {e}")

    return None


async def geocode_stores(input_path: str | None = None, output_path: str | None = None):
    """Geocode all stores and write results to a new CSV with lat/lng."""
    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_MAPS_API_KEY not set in .env")
        print("Geocoding requires a Google Maps API key.")
        print("Get one at: https://console.cloud.google.com → Geocoding API")
        return

    inp = Path(input_path) if input_path else RAW_DIR / "jan_aushadhi_stores.csv"
    if not inp.exists():
        print(f"ERROR: {inp} not found. Run scrapers/jan_aushadhi.py first.")
        return

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(output_path) if output_path else PROCESSED_DIR / "jan_aushadhi_stores_geocoded.csv"

    with open(inp, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        stores = list(reader)

    print(f"Geocoding {len(stores)} stores...")
    fieldnames = list(stores[0].keys()) + ["latitude", "longitude"]

    geocoded = 0
    failed = 0

    async with httpx.AsyncClient(timeout=10) as client:
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for i, store in enumerate(stores):
                coords = await geocode_address(
                    client,
                    store.get("address", ""),
                    store.get("pin_code", ""),
                    store.get("state", ""),
                )

                if coords:
                    store["latitude"] = coords[0]
                    store["longitude"] = coords[1]
                    geocoded += 1
                else:
                    store["latitude"] = ""
                    store["longitude"] = ""
                    failed += 1

                writer.writerow(store)
                await asyncio.sleep(RATE_LIMIT_DELAY)

                if (i + 1) % 100 == 0:
                    print(f"  Progress: {i+1}/{len(stores)} ({geocoded} geocoded, {failed} failed)")
                    f.flush()

    print(f"\nDone: {geocoded} geocoded, {failed} failed")
    print(f"Saved to: {out}")


async def update_db_coordinates():
    """Update PostGIS geometry column from geocoded CSV."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
    from app.core.database import engine
    from sqlalchemy import text

    csv_path = PROCESSED_DIR / "jan_aushadhi_stores_geocoded.csv"
    if not csv_path.exists():
        print("ERROR: Geocoded CSV not found. Run geocode_stores() first.")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        updates = [
            (row["store_code"], float(row["latitude"]), float(row["longitude"]))
            for row in reader
            if row.get("latitude") and row.get("longitude")
        ]

    async with engine.begin() as conn:
        for code, lat, lng in updates:
            await conn.execute(
                text("""
                    UPDATE jan_aushadhi_stores
                    SET location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                    WHERE name = :code
                """),
                {"lng": lng, "lat": lat, "code": code},
            )

    print(f"Updated {len(updates)} store coordinates in database")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(geocode_stores())
