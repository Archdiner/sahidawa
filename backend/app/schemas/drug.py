from uuid import UUID

from pydantic import BaseModel


class ParsedDrugQuery(BaseModel):
    """LLM-parsed output from user's raw medicine query."""

    drug_name: str
    salt_composition: str | None = None
    strength: str | None = None
    dosage_form: str | None = None
    confidence: float = 1.0


class GenericResult(BaseModel):
    name: str
    manufacturer: str
    strength: str
    pack_size: str | None
    mrp: float
    price_per_unit: float | None
    is_jan_aushadhi: bool


class DrugSearchResponse(BaseModel):
    brand_name: str
    salt_composition: str
    strength: str
    mrp: float
    pack_size: str | None
    cheapest_generic: GenericResult | None
    jan_aushadhi_option: GenericResult | None
    all_generics: list[GenericResult]
    savings_percent: float | None
    is_narrow_therapeutic_index: bool = False


class StoreResult(BaseModel):
    name: str
    address: str
    city: str | None
    pin_code: str | None
    phone: str | None
    distance_km: float | None


class FullQueryResponse(BaseModel):
    drug: DrugSearchResponse
    nearest_stores: list[StoreResult]
