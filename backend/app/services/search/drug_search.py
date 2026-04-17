"""Drug search service using Meilisearch for fuzzy, typo-tolerant lookups."""

from app.core.search import get_drug_index


def search_drugs(query: str, limit: int = 10) -> list[dict]:
    """Search the drug index with typo tolerance."""
    index = get_drug_index()
    results = index.search(query, {"limit": limit})
    return results["hits"]


def search_drugs_by_salt(salt_name: str, limit: int = 20) -> list[dict]:
    """Find all drugs matching a salt composition."""
    index = get_drug_index()
    results = index.search(salt_name, {"limit": limit, "filter": "is_generic = true"})
    return results["hits"]
