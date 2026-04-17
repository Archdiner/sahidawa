"""Drug lookup API — for internal testing and future web interface."""

from fastapi import APIRouter

from app.services.search.drug_search import search_drugs, search_drugs_by_salt

router = APIRouter(prefix="/drugs", tags=["drugs"])


@router.get("/search")
async def search(q: str, limit: int = 10):
    """Search drugs by name with typo tolerance."""
    hits = search_drugs(q, limit=limit)
    return {"query": q, "count": len(hits), "results": hits}


@router.get("/generics")
async def generics(salt: str, limit: int = 20):
    """Find all generic alternatives for a given salt composition."""
    hits = search_drugs_by_salt(salt, limit=limit)
    return {"salt": salt, "count": len(hits), "results": hits}
