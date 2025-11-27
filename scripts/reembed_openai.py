#!/usr/bin/env python3
"""
Re-embed all documents in Supabase with OpenAI text-embedding-3-small.
Fixes embedding model mismatch between stored vectors (all-MiniLM-L6-v2)
and query embeddings (OpenAI text-embedding-3-small).

Usage:
    export DATABASE_URL="postgresql://postgres.[project]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    export AI_GATEWAY_API_KEY="vck_..."  # or OPENAI_API_KEY
    python scripts/reembed_openai.py
"""

import os
import time
import sys
import psycopg2
from psycopg2.extras import execute_batch
from openai import OpenAI

# Configuration
BATCH_SIZE = 100  # Documents per embedding API call
COMMIT_EVERY = 500  # Commit transaction every N records
EMBEDDING_MODEL = "openai/text-embedding-3-small"  # AI Gateway format
EMBEDDING_DIM = 384


def get_database_url():
    """Get database URL from environment, checking multiple variable names."""
    for var_name in ['DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'POSTGRES_URL_NON_POOLING']:
        url = os.environ.get(var_name)
        if url:
            print(f"Using database URL from {var_name}")
            return url
    return None


def get_openai_client():
    """Initialize OpenAI client with AI Gateway or direct API."""
    api_key = os.environ.get("AI_GATEWAY_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "AI_GATEWAY_API_KEY or OPENAI_API_KEY environment variable required"
        )

    # Use AI Gateway if AI_GATEWAY_API_KEY is set, otherwise direct OpenAI
    if os.environ.get("AI_GATEWAY_API_KEY"):
        print("Using Vercel AI Gateway for embeddings")
        return OpenAI(
            api_key=api_key,
            base_url="https://ai-gateway.vercel.sh/v1"
        )
    else:
        print("Using direct OpenAI API for embeddings")
        return OpenAI(api_key=api_key)


def generate_embeddings_batch(client, texts, max_retries=3):
    """Generate embeddings for a batch of texts with retry logic."""
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
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

    # Get database URL
    database_url = get_database_url()
    if not database_url:
        print("ERROR: Database URL environment variable required.")
        print("Set DATABASE_URL, POSTGRES_URL, or POSTGRES_PRISMA_URL")
        return 1

    # Connect to database
    print("\nConnecting to Supabase PostgreSQL...")
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        print("Connected!")
    except Exception as e:
        print(f"ERROR: Failed to connect: {e}")
        return 1

    # Initialize OpenAI client
    print("\nInitializing OpenAI client...")
    try:
        client = get_openai_client()
    except ValueError as e:
        print(f"ERROR: {e}")
        cursor.close()
        conn.close()
        return 1

    # Fetch all documents
    print("\nFetching documents from vecs.conductor_sessions...")
    cursor.execute("""
        SELECT id, metadata->>'document' as document
        FROM vecs.conductor_sessions
        WHERE metadata->>'document' IS NOT NULL
        ORDER BY id
    """)
    docs = cursor.fetchall()
    print(f"Total documents: {len(docs)}")

    if not docs:
        print("No documents to process!")
        cursor.close()
        conn.close()
        return 0

    # Estimate cost
    avg_chars = sum(len(d[1]) for d in docs) / len(docs)
    est_tokens = (avg_chars / 4) * len(docs)  # ~4 chars per token
    est_cost = (est_tokens / 1_000_000) * 0.02
    print(f"\nEstimated tokens: {est_tokens:,.0f}")
    print(f"Estimated cost: ${est_cost:.2f}")

    # Process in batches
    print(f"\nProcessing {len(docs)} documents in batches of {BATCH_SIZE}...")
    start_time = time.time()
    total_processed = 0
    errors = 0

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        ids = [d[0] for d in batch]
        texts = [d[1] for d in batch]

        try:
            # Generate embeddings
            embeddings = generate_embeddings_batch(client, texts)

            # Validate embedding dimensions
            for emb in embeddings:
                if len(emb) != EMBEDDING_DIM:
                    raise ValueError(f"Unexpected dimension: {len(emb)}, expected {EMBEDDING_DIM}")

            # Update vectors in database (column is 'embedding' not 'vec')
            update_sql = """
                UPDATE vecs.conductor_sessions
                SET embedding = %s::vector
                WHERE id = %s
            """
            updates = [(emb, id) for emb, id in zip(embeddings, ids)]
            execute_batch(cursor, update_sql, updates, page_size=BATCH_SIZE)

            total_processed += len(batch)

        except Exception as e:
            print(f"  ERROR on batch {i//BATCH_SIZE}: {e}")
            errors += 1
            continue

        # Commit and report progress
        if (i + len(batch)) % COMMIT_EVERY == 0 or (i + len(batch)) >= len(docs):
            conn.commit()
            elapsed = time.time() - start_time
            rate = total_processed / elapsed if elapsed > 0 else 0
            remaining = len(docs) - total_processed
            eta = remaining / rate if rate > 0 else 0
            print(f"Progress: {total_processed}/{len(docs)} ({rate:.1f}/sec, ETA: {eta:.0f}s)")

    # Final commit
    conn.commit()

    # Report results
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"  Documents processed: {total_processed}")
    print(f"  Errors: {errors}")
    print(f"  Time: {elapsed:.1f} seconds")
    print(f"  Rate: {total_processed/elapsed:.1f} docs/sec")

    # Verify a sample
    print("\nVerifying sample embedding...")
    cursor.execute("""
        SELECT id, array_length(embedding::float[], 1) as dim
        FROM vecs.conductor_sessions
        LIMIT 1
    """)
    sample = cursor.fetchone()
    if sample:
        print(f"  Sample ID: {sample[0][:32]}...")
        print(f"  Embedding dimension: {sample[1]}")

    cursor.close()
    conn.close()

    print("\nDone! Test the API with:")
    print('  curl -X POST "https://doha-nsd97s-projects.vercel.app/api/chat" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"message": "5604 Soren Lane"}\'')

    return 0


if __name__ == "__main__":
    sys.exit(main())
