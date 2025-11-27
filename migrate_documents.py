#!/usr/bin/env python3
"""
Migration script to add document content from ChromaDB to Supabase metadata.
Uses Supabase Python client with service_role key to call bulk_update_documents RPC.

Usage:
    source .venv/bin/activate
    python migrate_documents.py
"""

import json
import time
from pathlib import Path
from supabase import create_client, Client

# Configuration
CHROMA_DOCS_PATH = Path("/tmp/chroma_docs.json")
BATCH_SIZE = 50  # Records per RPC call (keep small to avoid payload limits)

# Supabase credentials
SUPABASE_URL = "https://gxpcrohsbtndndypagie.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4cGNyb2hzYnRuZG5keXBhZ2llIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzkyMzY2MSwiZXhwIjoyMDc5NDk5NjYxfQ.2c95jzGzlFkHeiLHjXMlxoteW1mGTYCc3E99LKWmXB0"


def escape_for_jsonb(s: str) -> str:
    """Clean string for JSONB storage."""
    if s is None:
        return ''
    return s.replace("\x00", "")


def load_documents() -> list[dict]:
    """Load documents from ChromaDB export."""
    print("Loading documents from ChromaDB export...")
    with open(CHROMA_DOCS_PATH, 'r') as f:
        docs = json.load(f)
    print(f"Loaded {len(docs)} documents")
    return docs


def get_migrated_ids(supabase: Client) -> set[str]:
    """Get IDs of already migrated documents."""
    migrated = set()
    offset = 0
    limit = 1000

    while True:
        result = supabase.schema("vecs").table("conductor_sessions").select("id").not_.is_("metadata->document", "null").range(offset, offset + limit - 1).execute()

        if not result.data:
            break

        for row in result.data:
            migrated.add(row['id'])

        if len(result.data) < limit:
            break

        offset += limit
        print(f"  Fetched {len(migrated)} migrated IDs...")

    return migrated


def main():
    """Run the migration using Supabase Python client."""
    print("Connecting to Supabase...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Load documents
    docs = load_documents()

    # Get IDs to skip
    print("Fetching migrated IDs...")
    try:
        migrated_ids = get_migrated_ids(supabase)
        print(f"Found {len(migrated_ids)} already migrated")
    except Exception as e:
        print(f"Could not fetch migrated IDs: {e}")
        migrated_ids = set()

    pending = [d for d in docs if d['id'] not in migrated_ids]
    print(f"Pending migration: {len(pending)} documents")

    if not pending:
        print("All documents already migrated!")
        return 0

    # Sort by document size (smallest first for faster initial progress)
    pending.sort(key=lambda x: len(x['doc']))

    # Execute batch updates via RPC
    print(f"Executing batch updates ({BATCH_SIZE} records per RPC call)...")
    start_time = time.time()
    total_updated = 0
    errors = 0

    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i:i + BATCH_SIZE]

        # Prepare arrays for RPC call
        doc_ids = [d['id'] for d in batch]
        doc_contents = [escape_for_jsonb(d['doc']) for d in batch]

        try:
            result = supabase.rpc(
                "bulk_update_documents",
                {"doc_ids": doc_ids, "doc_contents": doc_contents}
            ).execute()

            updated = result.data if result.data else len(batch)
            total_updated += updated if isinstance(updated, int) else len(batch)

        except Exception as e:
            print(f"  Error on batch {i//BATCH_SIZE}: {e}")
            errors += 1
            # Continue with next batch
            continue

        # Progress update every 10 batches
        if (i // BATCH_SIZE) % 10 == 0:
            elapsed = time.time() - start_time
            rate = total_updated / elapsed if elapsed > 0 else 0
            remaining = len(pending) - i - len(batch)
            eta = remaining / rate if rate > 0 else 0
            print(f"Progress: {total_updated}/{len(pending)} ({rate:.1f}/sec, ETA: {eta:.0f}s)")

    # Final stats
    elapsed = time.time() - start_time
    print(f"\nMigration complete!")
    print(f"  Total processed: {total_updated} records")
    print(f"  Errors: {errors} batches")
    print(f"  Time: {elapsed:.1f} seconds")
    if elapsed > 0:
        print(f"  Rate: {total_updated/elapsed:.1f} records/sec")

    return 0


if __name__ == "__main__":
    exit(main())
