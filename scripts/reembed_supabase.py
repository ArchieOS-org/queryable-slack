#!/usr/bin/env python3
"""
Re-embed all documents in Supabase with OpenAI text-embedding-3-small.
Uses Supabase Python client with service_role key for direct SQL access.

Usage:
    source .venv/bin/activate
    python scripts/reembed_supabase.py
"""

import os
import time
import sys
from openai import OpenAI
from supabase import create_client, Client

# Configuration
BATCH_SIZE = 50  # Documents per embedding API call (smaller for stability)
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIM = 384

# Supabase credentials (from migrate_documents.py)
SUPABASE_URL = "https://gxpcrohsbtndndypagie.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4cGNyb2hzYnRuZG5keXBhZ2llIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzkyMzY2MSwiZXhwIjoyMDc5NDk5NjYxfQ.2c95jzGzlFkHeiLHjXMlxoteW1mGTYCc3E99LKWmXB0"


def get_openai_client():
    """Initialize OpenAI client with AI Gateway."""
    api_key = os.environ.get("AI_GATEWAY_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "AI_GATEWAY_API_KEY or OPENAI_API_KEY environment variable required"
        )

    print("Using Vercel AI Gateway for embeddings")
    return OpenAI(
        api_key=api_key.strip(),
        base_url="https://ai-gateway.vercel.sh/v1"
    )


def generate_embeddings_batch(client, texts, max_retries=3):
    """Generate embeddings for a batch of texts with retry logic."""
    # Truncate very long texts (OpenAI has token limits)
    truncated_texts = [t[:8000] if t else "" for t in texts]

    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=truncated_texts,
                dimensions=EMBEDDING_DIM,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  Error: {e}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def main():
    """Run the re-embedding migration."""
    print("=" * 60)
    print("Re-embedding Migration: OpenAI text-embedding-3-small")
    print("=" * 60)

    # Initialize clients
    print("\nInitializing Supabase client...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    print("Initializing OpenAI client...")
    try:
        openai_client = get_openai_client()
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    # Fetch all document IDs and content
    print("\nFetching documents from vecs.conductor_sessions...")

    # Fetch documents in batches using pagination
    all_docs = []
    offset = 0
    limit = 500

    while True:
        result = supabase.schema("vecs").table("conductor_sessions").select(
            "id", "metadata->document"
        ).range(offset, offset + limit - 1).execute()

        if not result.data:
            break

        for row in result.data:
            doc = row.get('document') or (row.get('metadata', {}) or {}).get('document', '')
            if doc:
                all_docs.append({'id': row['id'], 'document': doc})

        print(f"  Fetched {len(all_docs)} documents...")

        if len(result.data) < limit:
            break
        offset += limit

    print(f"Total documents: {len(all_docs)}")

    if not all_docs:
        print("No documents to process!")
        return 0

    # Process in batches
    print(f"\nProcessing {len(all_docs)} documents in batches of {BATCH_SIZE}...")
    start_time = time.time()
    total_processed = 0
    errors = 0

    for i in range(0, len(all_docs), BATCH_SIZE):
        batch = all_docs[i:i + BATCH_SIZE]
        ids = [d['id'] for d in batch]
        texts = [d['document'] for d in batch]

        try:
            # Generate embeddings
            embeddings = generate_embeddings_batch(openai_client, texts)

            # Validate embedding dimensions
            for emb in embeddings:
                if len(emb) != EMBEDDING_DIM:
                    raise ValueError(f"Unexpected dimension: {len(emb)}, expected {EMBEDDING_DIM}")

            # Update each record via Supabase
            for doc_id, emb in zip(ids, embeddings):
                # Convert embedding to string format for pgvector
                emb_str = '[' + ','.join(str(x) for x in emb) + ']'

                # Update using raw SQL via RPC (since we need to set vector type)
                supabase.schema("vecs").table("conductor_sessions").update({
                    "embedding": emb_str
                }).eq("id", doc_id).execute()

            total_processed += len(batch)

        except Exception as e:
            print(f"  ERROR on batch {i//BATCH_SIZE}: {e}")
            errors += 1
            continue

        # Report progress
        elapsed = time.time() - start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        remaining = len(all_docs) - total_processed
        eta = remaining / rate if rate > 0 else 0
        print(f"Progress: {total_processed}/{len(all_docs)} ({rate:.1f}/sec, ETA: {eta:.0f}s)")

    # Report results
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"  Documents processed: {total_processed}")
    print(f"  Errors: {errors}")
    print(f"  Time: {elapsed:.1f} seconds")
    if elapsed > 0:
        print(f"  Rate: {total_processed/elapsed:.1f} docs/sec")

    print("\nDone! Test the API with:")
    print('  curl -X POST "https://doha-nsd97s-projects.vercel.app/api/chat" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"message": "5604 Soren Lane"}\'')

    return 0


if __name__ == "__main__":
    sys.exit(main())
