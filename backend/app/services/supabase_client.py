"""Supabase client wrapper for SahiDawa backend."""

from supabase import create_client, Client
from app.core.config import settings

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_secret_key,
        )
    return _client


def get_drug_by_brand(brand_name: str, limit: int = 10) -> list[dict]:
    """Search drugs by brand name using trigram similarity."""
    client = get_client()
    resp = client.table("drugs").select(
        "id, brand_name, manufacturer, strength, dosage_form, pack_size, mrp, price_per_unit, salt_id"
    ).ilike(
        "brand_name", f"%{brand_name}%"
    ).limit(limit).execute()
    return resp.data


def get_drugs_by_salt(salt_id: str, strength: str | None = None, limit: int = 100) -> list[dict]:
    """Get all drugs with same salt (generics)."""
    client = get_client()
    query = client.table("drugs").select(
        "id, brand_name, manufacturer, strength, dosage_form, pack_size, mrp, price_per_unit, salt_id"
    ).eq("salt_id", salt_id)
    if strength:
        query = query.eq("strength", strength)
    resp = query.limit(limit).execute()
    return resp.data


def get_cheapest_generic(salt_id: str, reference_mrp: float, strength: str, exclude_id: str) -> dict | None:
    """Find cheapest generic for a given salt/strength."""
    client = get_client()
    resp = (
        client.table("drugs")
        .select("id, brand_name, manufacturer, strength, dosage_form, pack_size, mrp, price_per_unit")
        .eq("salt_id", salt_id)
        .eq("strength", strength)
        .neq("id", exclude_id)
        .lt("mrp", reference_mrp)
        .order("mrp", desc=False)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def get_top_generics(salt_id: str, strength: str, exclude_id: str, reference_mrp: float, limit: int = 5) -> list[dict]:
    """Get top N cheapest generics for a drug."""
    client = get_client()
    resp = (
        client.table("drugs")
        .select("id, brand_name, manufacturer, strength, dosage_form, pack_size, mrp, price_per_unit")
        .eq("salt_id", salt_id)
        .eq("strength", strength)
        .neq("id", exclude_id)
        .lt("mrp", reference_mrp)
        .order("mrp", desc=False)
        .limit(limit)
        .execute()
    )
    return resp.data


def get_salt_by_name(name: str) -> dict | None:
    """Find salt by name (exact or fuzzy)."""
    client = get_client()
    # Try exact match first
    resp = client.table("salts").select("*").eq("name", name).limit(1).execute()
    if resp.data:
        return resp.data[0]
    # Try case-insensitive partial match
    resp = client.table("salts").select("*").ilike("name", f"%{name}%").limit(1).execute()
    return resp.data[0] if resp.data else None


def get_salt_by_id(salt_id: str) -> dict | None:
    """Get salt by UUID."""
    client = get_client()
    resp = client.table("salts").select("*").eq("id", salt_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def get_ceiling_price(salt_name: str, dosage_form: str | None = None, strength: str | None = None) -> dict | None:
    """Get NPPA ceiling price for a salt."""
    client = get_client()
    query = client.table("nppa_ceiling_prices").select("*").eq("salt_name", salt_name)
    if dosage_form:
        query = query.eq("dosage_form", dosage_form)
    if strength:
        query = query.eq("strength", strength)
    resp = query.limit(1).execute()
    return resp.data[0] if resp.data else None


def find_stores_by_pin(pin_code: str, limit: int = 5) -> list[dict]:
    """Find Jan Aushadhi stores by pin code with prefix fallback."""
    client = get_client()
    # Try RPC first for prefix fallback
    resp = client.rpc(
        "find_stores_by_pin_with_prefix",
        {"pin": pin_code, "store_limit": limit}
    ).execute()
    return resp.data


def find_nearest_stores(lat: float, lng: float, radius_km: float = 10, limit: int = 5) -> list[dict]:
    """Find nearest Jan Aushadhi stores using PostGIS."""
    client = get_client()
    resp = client.rpc(
        "find_nearest_stores",
        {"lat": lat, "lng": lng, "radius_km": radius_km, "store_limit": limit}
    ).execute()
    return resp.data


def log_query(
    phone_hash: str,
    query_text: str,
    response_data: dict | None = None,
    response_time_ms: int | None = None,
    session_pin_code: str | None = None,
) -> None:
    """Log a drug query to the database."""
    client = get_client()
    client.table("query_logs").insert({
        "phone_hash": phone_hash,
        "query_text": query_text,
        "response_data": response_data,
        "response_time_ms": response_time_ms,
        "session_pin_code": session_pin_code,
    }).execute()