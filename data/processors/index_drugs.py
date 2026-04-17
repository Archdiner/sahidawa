"""Index drug data into Meilisearch for fast, typo-tolerant search.

Reads normalized drug data from PostgreSQL and indexes it
into Meilisearch with appropriate searchable/filterable fields.

TODO: Implement indexing pipeline.
"""


def index_all_drugs():
    """Load drugs from DB and push to Meilisearch index."""
    raise NotImplementedError("Implement Meilisearch drug indexing")
