#!/usr/bin/env python3
"""Bulk data migrator for SahiDawa — pushes all CSV data to Supabase via REST API.

Usage:
    python migrate_to_supabase.py --phase salts     # migrate salts
    python migrate_to_supabase.py --phase drugs     # migrate drugs
    python migrate_to_supabase.py --phase stores    # migrate stores
    python migrate_to_supabase.py --phase nppa      # migrate NPPA
    python migrate_to_supabase.py --phase all       # migrate everything

IMPORTANT: Run the schema SQL in Supabase SQL Editor FIRST:
    supabase_schema.sql

Requires: pip install httpx
"""

import argparse
import csv
import sys
import time
from pathlib import Path

# Add backend to path for config
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.core.config import settings


class SupabaseMigrator:
    def __init__(self):
        self.base_url = settings.supabase_url
        self.key = settings.supabase_secret_key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self.batch_size = 100
        self.total_inserted = 0

    def _post(self, table: str, records: list[dict]) -> dict:
        """Insert records into a table."""
        import httpx
        resp = httpx.post(
            f"{self.base_url}/rest/v1/{table}",
            headers=self.headers,
            json=records,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _bulk_insert(self, table: str, records: list[dict]) -> int:
        """Insert records in batches."""
        inserted = 0
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]
            try:
                result = self._post(table, batch)
                count = len(result) if isinstance(result, list) else 1
                inserted += count
                print(f"  Inserted {inserted}/{len(records)} into {table}")
            except Exception as e:
                print(f"  ERROR at batch {i}: {e}")
                # Try one by one for debugging
                for j, record in enumerate(batch):
                    try:
                        self._post(table, [record])
                        inserted += 1
                    except Exception as e2:
                        print(f"  FAILED record {j}: {e2}")
        return inserted

    # ─────────────────────────────────────────────────────────────────────────
    # Phase: Salts (1648 rows)
    # ─────────────────────────────────────────────────────────────────────────
    def migrate_salts(self, csv_path: str = "../data/processed/salt_compositions.csv"):
        print(f"\n=== MIGRATING SALTS from {csv_path} ===")
        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                # Split synonyms from pipe-delimited string into array
                synonyms_raw = row.get("synonyms", "")
                synonyms = [s.strip() for s in synonyms_raw.split("|") if s.strip()] if synonyms_raw else []
                records.append({
                    "id": row["id"],
                    "name": row["name"],
                    "synonyms": synonyms,
                })
        print(f"Loaded {len(records)} salt records")
        self.total_inserted += self._bulk_insert("salts", records)
        print(f"SALTS COMPLETE: {len(records)} inserted")

    # ─────────────────────────────────────────────────────────────────────────
    # Phase: Drugs (245987 rows)
    # ─────────────────────────────────────────────────────────────────────────
    def migrate_drugs(self, csv_path: str = "../data/processed/drugs.csv"):
        print(f"\n=== MIGRATING DRUGS from {csv_path} ===")
        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
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
                if len(records) >= 5000:
                    count = self._bulk_insert("drugs", records)
                    records = []
        if records:
            self._bulk_insert("drugs", records)
        print(f"DRUGS COMPLETE: inserted all {len(records)} remaining")

    # ─────────────────────────────────────────────────────────────────────────
    # Phase: Stores (7742 rows)
    # ─────────────────────────────────────────────────────────────────────────
    def migrate_stores(self, csv_path: str = "../data/raw/jan_aushadhi_stores.csv"):
        print(f"\n=== MIGRATING STORES from {csv_path} ===")
        # Note: lat/lng not in CSV — stores will have NULL location
        # Geocoding can be added later via Google Maps API
        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                records.append({
                    "store_code": row["store_code"],
                    "address": row["address"],
                    "city": row.get("district") or None,  # CSV uses 'district' for city
                    "district": row.get("district") or None,
                    "state": row.get("state") or None,
                    "pin_code": row.get("pin_code") or None,
                    "phone": row.get("phone") or None,
                    "status": row.get("status") or "Operational",
                    "latitude": None,
                    "longitude": None,
                })
                if len(records) >= 1000:
                    count = self._bulk_insert("jan_aushadhi_stores", records)
                    records = []
        if records:
            self._bulk_insert("jan_aushadhi_stores", records)
        print(f"STORES COMPLETE")

    # ─────────────────────────────────────────────────────────────────────────
    # Phase: NPPA (622 rows)
    # ─────────────────────────────────────────────────────────────────────────
    def migrate_nppa(self, csv_path: str = "../data/processed/nppa_matched.csv"):
        print(f"\n=== MIGRATING NPPA from {csv_path} ===")
        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                # Use salt_name from nppa_drug_name, not salt_id (which references drugs table)
                records.append({
                    "salt_name": row["nppa_drug_name"],
                    "dosage_form": row.get("dosage_form") or None,
                    "strength": row.get("strength") or None,
                    "ceiling_price": float(row.get("ceiling_price_2026", 0)),
                    "unit": row.get("unit") or None,
                    "so_number": row.get("so_number") or None,
                    "so_date": row.get("so_date") or None,
                })
        self._bulk_insert("nppa_ceiling_prices", records)
        print(f"NPPA COMPLETE: {len(records)} inserted")

    # ─────────────────────────────────────────────────────────────────────────
    # Verify
    # ─────────────────────────────────────────────────────────────────────────
    def verify(self):
        """Verify data in all tables."""
        import httpx
        tables = ["salts", "drugs", "jan_aushadhi_stores", "nppa_ceiling_prices"]
        print("\n=== VERIFICATION ===")
        for table in tables:
            resp = httpx.get(
                f"{self.base_url}/rest/v1/{table}?select=count",
                headers=self.headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                count = data[0].get("count", "?") if data else "?"
                print(f"  {table}: {count} rows")
            else:
                print(f"  {table}: ERROR {resp.status_code} - {resp.text[:100]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SahiDawa data to Supabase")
    parser.add_argument("--phase", choices=["salts", "drugs", "stores", "nppa", "all", "verify"], default="all")
    args = parser.parse_args()

    migrator = SupabaseMigrator()

    if args.phase == "verify":
        migrator.verify()
    elif args.phase == "all":
        migrator.migrate_salts()
        time.sleep(1)
        migrator.migrate_drugs()
        time.sleep(1)
        migrator.migrate_stores()
        time.sleep(1)
        migrator.migrate_nppa()
        time.sleep(1)
        migrator.verify()
    else:
        getattr(migrator, f"migrate_{args.phase}")()

    print("\n=== MIGRATION COMPLETE ===")