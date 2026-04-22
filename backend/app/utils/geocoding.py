"""Geocoding utilities — convert lat/lng to Indian pin codes via Google Geocoding API."""

import httpx
from app.core.config import settings

GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def get_pin_code_from_coords(lat: float, lng: float) -> str | None:
    """Reverse geocode lat/lng to an Indian PIN code.

    Returns the 6-digit PIN code if found, None otherwise.
    """
    if not settings.google_maps_api_key:
        return None

    params = {
        "latlng": f"{lat},{lng}",
        "result_type": "postal_code",
        "key": settings.google_maps_api_key,
    }

    with httpx.Client(timeout=10.0) as client:
        try:
            resp = client.get(GOOGLE_GEOCODING_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            if not results:
                return None

            for result in results:
                address_components = result.get("address_components", [])
                for component in address_components:
                    types = component.get("types", [])
                    if "postal_code" in types:
                        return component.get("long_name")

            return None
        except Exception:
            return None


def get_address_from_coords(lat: float, lng: float) -> str | None:
    """Get the formatted address from lat/lng coordinates."""
    if not settings.google_maps_api_key:
        return None

    params = {
        "latlng": f"{lat},{lng}",
        "result_type": "street_address|route|locality|sublocality",
        "key": settings.google_maps_api_key,
    }

    with httpx.Client(timeout=10.0) as client:
        try:
            resp = client.get(GOOGLE_GEOCODING_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            if not results:
                return None

            return results[0].get("formatted_address")
        except Exception:
            return None