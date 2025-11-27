"""
Reindex script for adding entity metadata to existing sessions.

This script processes existing sessions in ChromaDB/Supabase and adds
entity extraction metadata without requiring a full re-ingestion.

Usage:
    python -m conductor.reindex [--use-llm] [--batch-size 50] [--dry-run]
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

import chromadb

from conductor.entity_extractor import (
    extract_entities,
    group_entities_by_type,
    get_entity_list,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def extract_entities_for_document(
    document: str, use_llm: bool = False
) -> Dict[str, str]:
    """
    Extract entities from a document and return ChromaDB-compatible metadata.

    Args:
        document: Text content to extract entities from
        use_llm: Whether to use LLM for extraction

    Returns:
        Dictionary with entity metadata fields (CSV strings)
    """
    try:
        result = extract_entities(document, use_llm=use_llm)
        grouped = group_entities_by_type(result.entities)

        # Convert to CSV strings for ChromaDB compatibility
        person_mentions = ",".join(get_entity_list(result.entities, "PERSON"))
        address_mentions = ",".join(get_entity_list(result.entities, "ADDRESS"))
        deal_mentions = ",".join(get_entity_list(result.entities, "DEAL"))
        company_mentions = ",".join(get_entity_list(result.entities, "COMPANY"))
        price_mentions = ",".join(get_entity_list(result.entities, "PRICE"))

        # Create entities CSV (TYPE:value format)
        entities_parts = []
        for entity_type, values in grouped.items():
            for value in values:
                entities_parts.append(f"{entity_type}:{value}")
        entities_csv = ",".join(entities_parts)

        return {
            "entities": entities_csv,
            "person_mentions": person_mentions,
            "address_mentions": address_mentions,
            "deal_mentions": deal_mentions,
            "company_mentions": company_mentions,
            "price_mentions": price_mentions,
            "is_chunk": False,
        }

    except Exception as e:
        logger.warning(f"Entity extraction failed: {e}")
        return {
            "entities": "",
            "person_mentions": "",
            "address_mentions": "",
            "deal_mentions": "",
            "company_mentions": "",
            "price_mentions": "",
            "is_chunk": False,
        }


def reindex_chromadb(
    db_path: Path = Path("./conductor_db"),
    collection_name: str = "conductor_sessions",
    use_llm: bool = False,
    batch_size: int = 50,
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Reindex existing ChromaDB sessions with entity metadata.

    Args:
        db_path: Path to ChromaDB persistent storage
        collection_name: Name of the collection to reindex
        use_llm: Whether to use LLM for entity extraction
        batch_size: Number of records to process per batch
        dry_run: If True, don't actually update the database

    Returns:
        Dictionary with reindexing statistics
    """
    stats = {
        "total": 0,
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    try:
        client = chromadb.PersistentClient(path=str(db_path))
        collection = client.get_collection(name=collection_name)

        # Get total count
        stats["total"] = collection.count()
        logger.info(f"Found {stats['total']} documents in collection '{collection_name}'")

        if stats["total"] == 0:
            logger.info("No documents to reindex")
            return stats

        # Process in batches
        offset = 0
        while offset < stats["total"]:
            # Fetch batch of documents
            results = collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas"],
            )

            if not results["ids"]:
                break

            batch_ids = results["ids"]
            batch_docs = results["documents"]
            batch_metas = results["metadatas"]

            logger.info(
                f"Processing batch {offset // batch_size + 1}: "
                f"{len(batch_ids)} documents (offset {offset})"
            )

            # Process each document in batch
            updated_ids = []
            updated_docs = []
            updated_metas = []

            for i, (doc_id, document, metadata) in enumerate(
                zip(batch_ids, batch_docs, batch_metas)
            ):
                stats["processed"] += 1

                # Skip if already has entity metadata
                if metadata.get("entities") or metadata.get("person_mentions"):
                    logger.debug(f"Skipping {doc_id}: already has entity metadata")
                    stats["skipped"] += 1
                    continue

                # Skip chunks (they get entities from parent)
                if metadata.get("is_chunk"):
                    logger.debug(f"Skipping {doc_id}: is a chunk")
                    stats["skipped"] += 1
                    continue

                try:
                    # Extract entities
                    entity_metadata = extract_entities_for_document(
                        document, use_llm=use_llm
                    )

                    # Merge with existing metadata
                    updated_metadata = {**metadata, **entity_metadata}

                    updated_ids.append(doc_id)
                    updated_docs.append(document)
                    updated_metas.append(updated_metadata)

                    stats["updated"] += 1

                    # Log progress
                    entity_count = len(entity_metadata.get("entities", "").split(","))
                    if entity_metadata.get("entities"):
                        logger.debug(
                            f"Extracted {entity_count} entities from {doc_id}"
                        )

                except Exception as e:
                    logger.error(f"Failed to process {doc_id}: {e}")
                    stats["errors"] += 1

            # Upsert updated documents
            if updated_ids and not dry_run:
                collection.upsert(
                    ids=updated_ids,
                    documents=updated_docs,
                    metadatas=updated_metas,
                )
                logger.info(f"Updated {len(updated_ids)} documents in batch")
            elif updated_ids and dry_run:
                logger.info(f"[DRY RUN] Would update {len(updated_ids)} documents")

            offset += batch_size

        return stats

    except Exception as e:
        logger.exception(f"Reindexing failed: {e}")
        raise


def reindex_supabase(
    use_llm: bool = False,
    batch_size: int = 50,
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Reindex existing Supabase sessions with entity metadata.

    Args:
        use_llm: Whether to use LLM for entity extraction
        batch_size: Number of records to process per batch
        dry_run: If True, don't actually update the database

    Returns:
        Dictionary with reindexing statistics
    """
    try:
        from supabase import create_client, Client

        supabase_url = os.environ.get("SUPABASE_URL", "").strip()
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for reindexing"
            )

        client = create_client(supabase_url, supabase_key)

    except ImportError:
        logger.error("supabase package not installed. Run: pip install supabase")
        return {"error": "supabase not installed"}
    except ValueError as e:
        logger.error(str(e))
        return {"error": str(e)}

    stats = {
        "total": 0,
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    try:
        # Get all sessions from vecs schema
        result = (
            client.schema("vecs")
            .from_("conductor_sessions")
            .select("id, metadata")
            .execute()
        )

        if not result.data:
            logger.info("No sessions found in Supabase")
            return stats

        stats["total"] = len(result.data)
        logger.info(f"Found {stats['total']} sessions in Supabase")

        # Process in batches
        for i in range(0, len(result.data), batch_size):
            batch = result.data[i : i + batch_size]
            logger.info(
                f"Processing batch {i // batch_size + 1}: {len(batch)} sessions"
            )

            for row in batch:
                stats["processed"] += 1
                session_id = row["id"]
                metadata = row.get("metadata", {})

                # Skip if already has entity metadata
                if metadata.get("entities") or metadata.get("person_mentions"):
                    stats["skipped"] += 1
                    continue

                # Get document text from metadata
                document = metadata.get("document", "")
                if not document:
                    stats["skipped"] += 1
                    continue

                try:
                    # Extract entities
                    entity_metadata = extract_entities_for_document(
                        document, use_llm=use_llm
                    )

                    # Merge with existing metadata
                    updated_metadata = {**metadata, **entity_metadata}

                    if not dry_run:
                        # Update in Supabase
                        client.schema("vecs").from_("conductor_sessions").update(
                            {"metadata": updated_metadata}
                        ).eq("id", session_id).execute()

                    stats["updated"] += 1

                except Exception as e:
                    logger.error(f"Failed to process {session_id}: {e}")
                    stats["errors"] += 1

            if dry_run:
                logger.info(f"[DRY RUN] Would update batch of {len(batch)} sessions")

        return stats

    except Exception as e:
        logger.exception(f"Supabase reindexing failed: {e}")
        raise


def main():
    """Main entry point for reindex script."""
    parser = argparse.ArgumentParser(
        description="Reindex existing sessions with entity metadata"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("./conductor_db"),
        help="Path to ChromaDB database (default: ./conductor_db)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="conductor_sessions",
        help="ChromaDB collection name (default: conductor_sessions)",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for entity extraction (slower but more accurate)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of records to process per batch (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually update the database, just log what would be done",
    )
    parser.add_argument(
        "--supabase",
        action="store_true",
        help="Reindex Supabase instead of ChromaDB",
    )

    args = parser.parse_args()

    logger.info("Starting reindex operation")
    logger.info(f"  Use LLM: {args.use_llm}")
    logger.info(f"  Batch size: {args.batch_size}")
    logger.info(f"  Dry run: {args.dry_run}")

    if args.supabase:
        logger.info("  Target: Supabase")
        stats = reindex_supabase(
            use_llm=args.use_llm,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
    else:
        logger.info(f"  Target: ChromaDB at {args.db_path}")
        stats = reindex_chromadb(
            db_path=args.db_path,
            collection_name=args.collection,
            use_llm=args.use_llm,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

    logger.info("Reindex complete!")
    logger.info(f"  Total: {stats.get('total', 0)}")
    logger.info(f"  Processed: {stats.get('processed', 0)}")
    logger.info(f"  Updated: {stats.get('updated', 0)}")
    logger.info(f"  Skipped: {stats.get('skipped', 0)}")
    logger.info(f"  Errors: {stats.get('errors', 0)}")


if __name__ == "__main__":
    main()
