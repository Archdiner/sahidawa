import meilisearch

from app.core.config import settings

meili_client = meilisearch.Client(settings.meili_url, settings.meili_master_key)

DRUG_INDEX = "drugs"


def get_drug_index():
    return meili_client.index(DRUG_INDEX)


def setup_drug_index():
    """Create and configure the drugs index with searchable/filterable attributes."""
    index = meili_client.index(DRUG_INDEX)
    index.update_settings(
        {
            "searchableAttributes": [
                "brand_name",
                "salt_composition",
                "manufacturer",
                "salt_synonyms",
            ],
            "filterableAttributes": [
                "dosage_form",
                "strength",
                "is_generic",
                "manufacturer",
            ],
            "sortableAttributes": ["price_per_unit", "brand_name"],
            "typoTolerance": {
                "enabled": True,
                "minWordSizeForTypos": {"oneTypo": 3, "twoTypos": 6},
            },
        }
    )
    return index
