"""
Entity-aware semantic search for Conductor.

Provides enhanced search capabilities that combine:
- Vector similarity search (semantic matching)
- Entity-based filtering (person, address, channel)
- Query classification integration

This module integrates with both ChromaDB (local) and Supabase (cloud)
vector stores, using the entity metadata added during ingestion.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple

from sentence_transformers import SentenceTransformer

from conductor.query_classifier import classify_query, extract_entities
from conductor.supabase_query import (
    query_vector_similarity,
    query_with_entity_filter,
    get_supabase_client,
)

logger = logging.getLogger(__name__)

# Default embedding model (matches ChromaDB default)
DEFAULT_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


class EntitySearcher:
    """
    Entity-aware semantic search engine.

    Combines vector similarity with entity filtering for more precise results.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        use_supabase: bool = True,
    ):
        """
        Initialize the entity searcher.

        Args:
            model_name: Sentence transformer model for embeddings
            use_supabase: Whether to use Supabase (True) or ChromaDB (False)
        """
        self.model_name = model_name
        self.use_supabase = use_supabase
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query string.

        Args:
            query: Query text to encode

        Returns:
            List of floats representing the embedding vector
        """
        embedding = self.model.encode(query)
        return embedding.tolist()

    def search(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.0,
        person: Optional[str] = None,
        address: Optional[str] = None,
        channel: Optional[str] = None,
        use_query_entities: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform entity-aware semantic search.

        Args:
            query: Search query text
            limit: Maximum number of results
            threshold: Minimum similarity threshold (0.0 to 1.0)
            person: Filter by person name
            address: Filter by address
            channel: Filter by channel name
            use_query_entities: Auto-extract entities from query for filtering

        Returns:
            Search results with documents, metadata, and similarity scores
        """
        # Step 1: Classify query and extract entities if requested
        detected_entities = []
        if use_query_entities:
            detected_entities = extract_entities(query)
            logger.info(f"Detected entities in query: {detected_entities}")

            # Auto-populate person filter from detected entities
            if not person and detected_entities:
                # Use first detected entity as person filter
                person = detected_entities[0]
                logger.info(f"Using detected entity as person filter: {person}")

        # Step 2: Generate query embedding
        query_embedding = self.encode_query(query)

        # Step 3: Execute search with filters
        if self.use_supabase:
            results = self._search_supabase(
                query_embedding=query_embedding,
                limit=limit,
                threshold=threshold,
                person=person,
                address=address,
                channel=channel,
            )
        else:
            results = self._search_chromadb(
                query_embedding=query_embedding,
                limit=limit,
                threshold=threshold,
                person=person,
                address=address,
                channel=channel,
            )

        # Step 4: Enhance results with entity info
        results["query_entities"] = detected_entities
        results["filters_applied"] = {
            "person": person,
            "address": address,
            "channel": channel,
        }

        return results

    def _search_supabase(
        self,
        query_embedding: List[float],
        limit: int,
        threshold: float,
        person: Optional[str],
        address: Optional[str],
        channel: Optional[str],
    ) -> Dict[str, Any]:
        """Execute search against Supabase."""
        try:
            # Use entity-filtered search if filters provided
            if person or address or channel:
                return query_with_entity_filter(
                    query_embedding=query_embedding,
                    match_threshold=threshold,
                    match_count=limit,
                    person=person,
                    address=address,
                    channel=channel,
                )
            else:
                return query_vector_similarity(
                    query_embedding=query_embedding,
                    match_threshold=threshold,
                    match_count=limit,
                    channel_name=channel,
                )
        except Exception as e:
            logger.error(f"Supabase search failed: {e}")
            raise

    def _search_chromadb(
        self,
        query_embedding: List[float],
        limit: int,
        threshold: float,
        person: Optional[str],
        address: Optional[str],
        channel: Optional[str],
    ) -> Dict[str, Any]:
        """Execute search against ChromaDB."""
        try:
            import chromadb

            client = chromadb.PersistentClient(path="./conductor_db")
            collection = client.get_collection(name="conductor_sessions")

            # Build where filter for metadata
            where_filter = None
            if channel:
                where_filter = {"channel": channel}

            # Build where_document filter for entity text search
            where_document = None
            if person:
                where_document = {"$contains": person}
            elif address:
                where_document = {"$contains": address}

            # Execute query
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter,
                where_document=where_document,
                include=["documents", "metadatas", "distances"],
            )

            return results

        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            raise


def search_with_entities(
    query: str,
    limit: int = 5,
    threshold: float = 0.0,
    person: Optional[str] = None,
    address: Optional[str] = None,
    channel: Optional[str] = None,
    use_supabase: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function for entity-aware search.

    Args:
        query: Search query text
        limit: Maximum number of results
        threshold: Minimum similarity threshold
        person: Filter by person name
        address: Filter by address
        channel: Filter by channel name
        use_supabase: Use Supabase (True) or ChromaDB (False)

    Returns:
        Search results with documents and metadata
    """
    searcher = EntitySearcher(use_supabase=use_supabase)
    return searcher.search(
        query=query,
        limit=limit,
        threshold=threshold,
        person=person,
        address=address,
        channel=channel,
    )


def format_search_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format raw search results into a cleaner structure.

    Args:
        results: Raw search results from ChromaDB/Supabase

    Returns:
        List of formatted result dictionaries
    """
    formatted = []

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i, (doc_id, document, metadata, distance) in enumerate(
        zip(ids, documents, metadatas, distances)
    ):
        similarity = 1.0 - distance  # Convert distance to similarity

        formatted.append({
            "rank": i + 1,
            "id": doc_id,
            "similarity": round(similarity, 4),
            "document": document[:500] + "..." if len(document) > 500 else document,
            "metadata": {
                "channel": metadata.get("channel", ""),
                "date": metadata.get("date", ""),
                "message_count": metadata.get("message_count", 0),
                "person_mentions": metadata.get("person_mentions", ""),
                "address_mentions": metadata.get("address_mentions", ""),
            },
        })

    return formatted


def search_by_entity_type(
    entity_type: str,
    entity_value: str,
    query: Optional[str] = None,
    limit: int = 10,
    use_supabase: bool = True,
) -> Dict[str, Any]:
    """
    Search primarily by entity type and value.

    Args:
        entity_type: Type of entity (PERSON, ADDRESS, DEAL, etc.)
        entity_value: Value to search for
        query: Optional semantic query to combine with entity filter
        limit: Maximum results
        use_supabase: Use Supabase or ChromaDB

    Returns:
        Search results filtered by entity
    """
    searcher = EntitySearcher(use_supabase=use_supabase)

    # Map entity type to filter parameter
    filter_kwargs = {}
    if entity_type.upper() == "PERSON":
        filter_kwargs["person"] = entity_value
    elif entity_type.upper() == "ADDRESS":
        filter_kwargs["address"] = entity_value
    elif entity_type.upper() == "CHANNEL":
        filter_kwargs["channel"] = entity_value

    # If no query provided, use entity value as query
    search_query = query if query else f"conversations about {entity_value}"

    return searcher.search(
        query=search_query,
        limit=limit,
        use_query_entities=False,  # Already have explicit entity
        **filter_kwargs,
    )


def get_entity_mentions(
    entity_value: str,
    entity_type: str = "PERSON",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Find all sessions mentioning a specific entity.

    Args:
        entity_value: Entity to search for
        entity_type: Type of entity
        limit: Maximum results

    Returns:
        List of sessions mentioning the entity
    """
    results = search_by_entity_type(
        entity_type=entity_type,
        entity_value=entity_value,
        limit=limit,
    )

    return format_search_results(results)
