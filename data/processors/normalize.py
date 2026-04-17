"""LLM-powered salt normalization pipeline.

Takes raw drug entries from scraped sources and normalizes them into
structured salt composition mappings using batch LLM processing.

Workflow:
1. Read raw drug entries (brand name, composition string)
2. Send to LLM for structured extraction
3. Cluster synonyms (Paracetamol = Acetaminophen = PCM)
4. Write normalized data to PostgreSQL

TODO: Implement batch processing pipeline.
"""


def normalize_salt_compositions(raw_entries: list[dict]) -> list[dict]:
    """Use LLM to normalize raw salt composition strings."""
    raise NotImplementedError("Implement LLM-based salt normalization")
