"""
Deep research query function optimized for Vercel deployment with Supabase.

Implements multi-query generation, hybrid search, and RRF fusion for exhaustive retrieval.
Now supports adaptive parameters based on query classification.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from anthropic import Anthropic
from conductor.multi_query import generate_query_variations, generate_entity_focused_variations
from conductor.rank_fusion import fuse_chromadb_results
from conductor.supabase_query import query_vector_similarity

logger = logging.getLogger(__name__)


def deep_research_query(
    query_text: str,
    query_embedding: List[float],
    deep_research_n_results: int = 50,
    max_final_results: int = 40,
    num_query_variations: int = 7,
    classification: Optional[Any] = None
) -> Dict:
    """
    Perform exhaustive deep research using multi-query retrieval and RRF fusion.

    This function is optimized for Vercel deployment with Supabase vector search.
    Supports adaptive parameters based on query classification for analytical queries.

    Args:
        query_text: Original user query string
        query_embedding: Pre-computed embedding for the original query
        deep_research_n_results: Number of results per query variation (default: 50)
        max_final_results: Maximum final results after RRF fusion (default: 40)
        num_query_variations: Number of query variations to generate (default: 7)
        classification: Optional QueryClassification object from query_classifier

    Returns:
        Dictionary with fused query results containing documents, metadatas, distances
    """
    # Adaptive parameters based on classification
    is_analytical = False
    entities = []
    dimensions = []

    if classification is not None:
        is_analytical = classification.query_type in ("analytical", "comparative", "behavioral")
        entities = classification.entities_mentioned
        dimensions = classification.analysis_dimensions

        # Boost retrieval for analytical queries (balanced for Vercel 60s timeout)
        if is_analytical:
            deep_research_n_results = max(deep_research_n_results, 60)  # 60 per variation (was 75)
            max_final_results = max(max_final_results, 50)  # 50 final results (was 60)
            num_query_variations = max(num_query_variations, 8)  # 8 variations (was 10)
            logger.info(f"Analytical query detected - boosted params: "
                        f"n_results={deep_research_n_results}, "
                        f"final={max_final_results}, "
                        f"variations={num_query_variations}")

    logger.info(f"Starting deep research mode: {query_text[:50]}...")

    # Step 1: Generate query variations (use entity-focused for analytical queries)
    logger.info(f"Step 1/3: Generating {num_query_variations} query variations...")
    try:
        # Use entity-focused generation for analytical queries with detected entities
        if is_analytical and entities:
            logger.info(f"Using entity-focused generation for entities: {entities}")
            query_variations = generate_entity_focused_variations(
                query_text,
                entities=entities,
                dimensions=dimensions,
                num_variations=num_query_variations
            )
        else:
            query_variations = generate_query_variations(query_text, num_variations=num_query_variations)
        logger.info(f"Generated {len(query_variations)} query variations")
    except Exception as e:
        logger.error(f"Failed to generate query variations: {e}")
        logger.warning("Falling back to single query")
        query_variations = [query_text]

    # Step 2: Generate embeddings and query for each variation
    logger.info(f"Step 2/3: Querying with {len(query_variations)} variations...")

    # For the first query (original), we already have the embedding
    # For others, we need to generate embeddings
    from openai import OpenAI
    ai_gateway_key = os.getenv("AI_GATEWAY_API_KEY", "").strip()

    if not ai_gateway_key:
        logger.warning("AI_GATEWAY_API_KEY not set, using only original query")
        query_variations = [query_text]

    openai_client = OpenAI(
        api_key=ai_gateway_key,
        base_url="https://ai-gateway.vercel.sh/v1",
    ) if ai_gateway_key else None

    result_sets = []
    total_retrieved = 0

    for i, query_var in enumerate(query_variations):
        logger.info(f"Query variation {i+1}/{len(query_variations)}: {query_var[:60]}...")

        try:
            # Use pre-computed embedding for original query, generate for others
            if i == 0:
                embedding = query_embedding
            else:
                if not openai_client:
                    logger.warning(f"Skipping variation {i+1}: No OpenAI client")
                    continue

                response = openai_client.embeddings.create(
                    model="openai/text-embedding-3-small",
                    input=query_var,
                    dimensions=384,
                    encoding_format="float",
                )
                embedding = response.data[0].embedding

            # Query Supabase with this embedding
            results = query_vector_similarity(
                query_embedding=embedding,
                match_threshold=0.0,
                match_count=deep_research_n_results
            )

            if results.get("documents") and results["documents"][0]:
                num_results = len(results["documents"][0])
                result_sets.append(results)
                total_retrieved += num_results
                logger.info(f"  Retrieved {num_results} results from variation {i+1}")
            else:
                logger.warning(f"  No results from variation {i+1}")

        except Exception as e:
            logger.error(f"  Error retrieving results for variation {i+1}: {e}")
            continue

    logger.info(f"Retrieved {total_retrieved} total results from {len(result_sets)} successful queries")

    if not result_sets:
        logger.warning("No results retrieved from any query variation")
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    # Step 3: Fuse results using RRF
    logger.info(f"Step 3/3: Fusing {len(result_sets)} result sets using RRF...")
    try:
        fused_results = fuse_chromadb_results(
            result_sets,
            k=60,  # Standard RRF constant
            top_k=max_final_results
        )

        num_fused = len(fused_results.get('documents', [[]])[0])
        logger.info(f"RRF fusion complete: {num_fused} unique results from {total_retrieved} initial retrievals")
    except Exception as e:
        logger.error(f"Failed to fuse results with RRF: {e}")
        # Fallback: use first result set
        logger.warning("Falling back to first result set")
        fused_results = result_sets[0] if result_sets else {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    logger.info(f"Deep research complete: {len(fused_results.get('documents', [[]])[0])} final results")
    return fused_results
