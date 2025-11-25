#!/usr/bin/env python3
"""
Migration script to add document content from ChromaDB to Supabase metadata.
Reads from pre-exported JSON and executes SQL batches via direct postgres connection.

Usage:
    export DATABASE_URL="postgresql://postgres.[project]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    python migrate_docs.py
"""

import json
import os
import time
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path

# Configuration
CHROMA_DOCS_PATH = Path("/tmp/chroma_docs.json")
BATCH_SIZE = 100  # Records per execute_batch page
COMMIT_EVERY = 1000  # Commit transaction every N records


def escape_for_jsonb(s: str) -> str:
    """Clean string for JSONB storage."""
    if s is None:
        return ''
    # Remove null bytes that break PostgreSQL
    return s.replace("\x00", "")


def load_documents() -> list[dict]:
    """Load documents from ChromaDB export."""
    print("Loading documents from ChromaDB export...")
    with open(CHROMA_DOCS_PATH, 'r') as f:
        docs = json.load(f)
    print(f"Loaded {len(docs)} documents")
    return docs


def get_migrated_count(cursor) -> int:
    """Get count of already migrated documents."""
    cursor.execute(
        "SELECT COUNT(*) FROM vecs.conductor_sessions WHERE metadata->>'document' IS NOT NULL"
    )
    return cursor.fetchone()[0]


def get_migrated_ids(cursor) -> set[str]:
    """Get IDs of already migrated documents."""
    cursor.execute(
        "SELECT id FROM vecs.conductor_sessions WHERE metadata->>'document' IS NOT NULL"
    )
    return {row[0] for row in cursor.fetchall()}


def main():
    """Run the migration using psycopg2 execute_batch."""
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable required.")
        print("Format: postgresql://postgres.[project]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres")
        print("\nGet it from: Supabase Dashboard > Settings > Database > Connection string > URI")
        return 1

    # Load documents
    docs = load_documents()

    # Connect to database
    print("Connecting to Supabase PostgreSQL...")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    # Check current migration state
    migrated_count = get_migrated_count(cursor)
    print(f"Already migrated: {migrated_count} documents")

    if migrated_count >= len(docs):
        print("All documents already migrated!")
        cursor.close()
        conn.close()
        return 0

    # Get IDs to skip
    print("Fetching migrated IDs...")
    migrated_ids = get_migrated_ids(cursor)
    pending = [d for d in docs if d['id'] not in migrated_ids]
    print(f"Pending migration: {len(pending)} documents")

    if not pending:
        print("All documents already migrated!")
        cursor.close()
        conn.close()
        return 0

    # Prepare update data: list of (metadata_json, id) tuples
    print("Preparing update data...")
    update_data = []
    for doc in pending:
        clean_doc = escape_for_jsonb(doc['doc'])
        # We'll use jsonb_set to add/update the 'document' key in metadata
        update_data.append((clean_doc, doc['id']))

    # Execute batch updates
    print(f"Executing batch updates ({BATCH_SIZE} records per batch)...")
    start_time = time.time()

    # SQL to update metadata with document
    update_sql = """
        UPDATE vecs.conductor_sessions
        SET metadata = metadata || jsonb_build_object('document', %s)
        WHERE id = %s
    """

    try:
        # Process in chunks with periodic commits
        total_updated = 0
        for i in range(0, len(update_data), COMMIT_EVERY):
            chunk = update_data[i:i + COMMIT_EVERY]

            execute_batch(
                cursor,
                update_sql,
                chunk,
                page_size=BATCH_SIZE
            )

            conn.commit()
            total_updated += len(chunk)

            elapsed = time.time() - start_time
            rate = total_updated / elapsed if elapsed > 0 else 0
            print(f"Progress: {total_updated}/{len(update_data)} records ({rate:.1f}/sec)")

        # Final verification
        final_count = get_migrated_count(cursor)
        elapsed = time.time() - start_time

        print(f"\nMigration complete!")
        print(f"  Total migrated: {final_count} records")
        print(f"  Time: {elapsed:.1f} seconds")
        print(f"  Rate: {len(update_data)/elapsed:.1f} records/sec")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return 0


if __name__ == "__main__":
    exit(main())
