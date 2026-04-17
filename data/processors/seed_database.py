"""Seed PostgreSQL from processed CSV files using COPY-style bulk inserts.

Prerequisites:
  - PostgreSQL + PostGIS running (docker compose up -d)
  - Database created (make migrate)
  - Processed data exists (python data/processors/ingest_medicines.py)

Usage:
  python data/processors/seed_database.py
"""

import asyncio
import csv
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import text

from app.core.database import engine


PROCESSED_DIR = Path(__file__).parent.parent / "processed"


async def seed_salt_compositions():
    """Bulk insert salt compositions from CSV."""
    csv_path = PROCESSED_DIR / "salt_compositions.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found. Run ingest_medicines.py first.")
        return 0

    async with engine.begin() as conn:
        # Clear existing data
        await conn.execute(text("TRUNCATE salt_compositions CASCADE"))

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                synonyms = row["synonyms"].split("|") if row["synonyms"] else []
                batch.append({
                    "id": row["id"],
                    "name": row["name"],
                    "synonyms": synonyms,
                    "is_narrow_therapeutic_index": False,
                })

            if batch:
                await conn.execute(
                    text("""
                        INSERT INTO salt_compositions (id, name, synonyms, is_narrow_therapeutic_index)
                        VALUES (:id, :name, :synonyms, :is_narrow_therapeutic_index)
                        ON CONFLICT (name) DO NOTHING
                    """),
                    batch,
                )

    print(f"  Seeded {len(batch)} salt compositions")
    return len(batch)


async def seed_drugs():
    """Bulk insert drugs from CSV in batches."""
    csv_path = PROCESSED_DIR / "drugs.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found. Run ingest_medicines.py first.")
        return 0

    total = 0
    BATCH_SIZE = 5000

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            batch.append({
                "id": row["id"],
                "brand_name": row["brand_name"],
                "manufacturer": row["manufacturer"],
                "salt_id": row["salt_id"],
                "strength": row["strength"] or "N/A",
                "dosage_form": row["dosage_form"] or "Unknown",
                "pack_size": row["pack_size"] or None,
                "mrp": float(row["mrp"]),
                "price_per_unit": float(row["price_per_unit"]) if row["price_per_unit"] else None,
            })

            if len(batch) >= BATCH_SIZE:
                async with engine.begin() as conn:
                    await conn.execute(
                        text("""
                            INSERT INTO drugs (id, brand_name, manufacturer, salt_id,
                                             strength, dosage_form, pack_size, mrp, price_per_unit)
                            VALUES (:id, :brand_name, :manufacturer, :salt_id,
                                   :strength, :dosage_form, :pack_size, :mrp, :price_per_unit)
                            ON CONFLICT DO NOTHING
                        """),
                        batch,
                    )
                total += len(batch)
                print(f"  Inserted {total:,} drugs...")
                batch = []

        # Final batch
        if batch:
            async with engine.begin() as conn:
                await conn.execute(
                    text("""
                        INSERT INTO drugs (id, brand_name, manufacturer, salt_id,
                                         strength, dosage_form, pack_size, mrp, price_per_unit)
                        VALUES (:id, :brand_name, :manufacturer, :salt_id,
                               :strength, :dosage_form, :pack_size, :mrp, :price_per_unit)
                        ON CONFLICT DO NOTHING
                    """),
                    batch,
                )
            total += len(batch)

    print(f"  Seeded {total:,} drugs total")
    return total


async def seed_jan_aushadhi_stores():
    """Bulk insert Jan Aushadhi stores from scraped CSV."""
    csv_path = Path(__file__).parent.parent / "raw" / "jan_aushadhi_stores.csv"
    if not csv_path.exists():
        print(f"  SKIP: {csv_path} not found. Run scrapers/jan_aushadhi.py first.")
        return 0

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE jan_aushadhi_stores CASCADE"))

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append({
                    "id": str(uuid.uuid4()),
                    "name": row.get("store_code", "Unknown"),
                    "address": row.get("address", ""),
                    "city": row.get("district", ""),
                    "state": row.get("state", ""),
                    "pin_code": row.get("pin_code", ""),
                    "phone": row.get("phone", "") or None,
                })

        if batch:
            # Insert in batches
            for i in range(0, len(batch), 1000):
                chunk = batch[i : i + 1000]
                await conn.execute(
                    text("""
                        INSERT INTO jan_aushadhi_stores (id, name, address, city, state, pin_code, phone)
                        VALUES (:id, :name, :address, :city, :state, :pin_code, :phone)
                    """),
                    chunk,
                )

    print(f"  Seeded {len(batch)} Jan Aushadhi stores")
    return len(batch)


async def main():
    print("=== SahiDawa Database Seeder ===\n")

    print("1. Seeding salt compositions...")
    salt_count = await seed_salt_compositions()

    print("2. Seeding drugs...")
    drug_count = await seed_drugs()

    print("3. Seeding Jan Aushadhi stores...")
    store_count = await seed_jan_aushadhi_stores()

    print(f"\n=== Done ===")
    print(f"  Salts:  {salt_count:,}")
    print(f"  Drugs:  {drug_count:,}")
    print(f"  Stores: {store_count:,}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
