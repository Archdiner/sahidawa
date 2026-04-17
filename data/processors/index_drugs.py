"""Index processed drug data into Meilisearch for fast fuzzy search.

Prerequisites:
  - Meilisearch running (docker compose up -d)
  - Processed data exists (python data/processors/ingest_medicines.py)

Usage:
  python data/processors/index_drugs.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.core.search import meili_client, DRUG_INDEX, setup_drug_index

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
BATCH_SIZE = 10000


def index_all_drugs():
    """Load JSONL documents and push to Meilisearch in batches."""
    jsonl_path = PROCESSED_DIR / "meili_drugs.jsonl"
    if not jsonl_path.exists():
        print(f"ERROR: {jsonl_path} not found. Run ingest_medicines.py first.")
        return

    print("Setting up Meilisearch index configuration...")
    setup_drug_index()

    print(f"Reading {jsonl_path}...")
    docs = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            docs.append(json.loads(line))

    print(f"Loaded {len(docs):,} documents")
    print(f"Indexing into '{DRUG_INDEX}' in batches of {BATCH_SIZE}...")

    index = meili_client.index(DRUG_INDEX)

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        task = index.add_documents(batch)
        print(f"  Batch {i // BATCH_SIZE + 1}: {len(batch)} docs → task {task.task_uid}")

    print(f"\nDone. {len(docs):,} documents queued for indexing.")
    print("Check status at: http://localhost:7700/tasks")


if __name__ == "__main__":
    index_all_drugs()
