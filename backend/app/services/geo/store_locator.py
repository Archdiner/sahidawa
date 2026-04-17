"""Geo service for finding nearest Jan Aushadhi stores."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.drug import StoreResult


async def find_nearest_stores(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    limit: int = 3,
    max_distance_km: float = 10.0,
) -> list[StoreResult]:
    """Find nearest Jan Aushadhi stores using PostGIS distance calculation."""
    query = text("""
        SELECT
            name,
            address,
            city,
            pin_code,
            phone,
            ST_Distance(
                location::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ) / 1000.0 AS distance_km
        FROM jan_aushadhi_stores
        WHERE location IS NOT NULL
          AND ST_DWithin(
              location::geography,
              ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
              :max_dist_m
          )
        ORDER BY distance_km
        LIMIT :limit
    """)
    result = await db.execute(
        query,
        {
            "lat": latitude,
            "lon": longitude,
            "max_dist_m": max_distance_km * 1000,
            "limit": limit,
        },
    )
    rows = result.fetchall()
    return [
        StoreResult(
            name=row.name,
            address=row.address,
            city=row.city,
            pin_code=row.pin_code,
            phone=row.phone,
            distance_km=round(row.distance_km, 1),
        )
        for row in rows
    ]


async def find_stores_by_pincode(
    db: AsyncSession, pin_code: str, limit: int = 3
) -> list[StoreResult]:
    """Find Jan Aushadhi stores by pin code."""
    query = text("""
        SELECT name, address, city, pin_code, phone
        FROM jan_aushadhi_stores
        WHERE pin_code = :pin_code
        LIMIT :limit
    """)
    result = await db.execute(query, {"pin_code": pin_code, "limit": limit})
    rows = result.fetchall()
    return [
        StoreResult(
            name=row.name,
            address=row.address,
            city=row.city,
            pin_code=row.pin_code,
            phone=row.phone,
            distance_km=None,
        )
        for row in rows
    ]
