"""Salt composition normalization — now integrated into ingest_medicines.py.

The original plan was to use LLM batch processing for normalization.
In practice, the Indian Medicine Dataset already has structured composition
fields that can be normalized with regex + synonym mapping.

See ingest_medicines.py for the actual implementation:
  - parse_composition(): extracts salt name + strength from "Paracetamol (500mg)"
  - normalize_salt_name(): maps synonyms (Acetaminophen → Paracetamol)
  - build_salt_index(): deduplicates 7,428 raw strings into 1,648 unique molecules

LLM normalization can be added later for:
  - Edge cases the regex misses
  - New drugs submitted by users
  - Cross-referencing CDSCO and NPPA data with different naming conventions
"""
