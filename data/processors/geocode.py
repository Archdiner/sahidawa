"""Geocode Jan Aushadhi store addresses to lat/lng coordinates.

Uses Google Maps Geocoding API or Nominatim (free) to convert
store addresses into geographic coordinates for PostGIS queries.

TODO: Implement geocoding pipeline.
"""


def geocode_stores(stores: list[dict]) -> list[dict]:
    """Geocode a list of store address dicts, adding lat/lng."""
    raise NotImplementedError("Implement store geocoding")
