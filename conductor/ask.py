"""
CLI for querying the semantic memory bank.

Provides command-line interface for semantic search.
"""

# CRITICAL: Set TOKENIZERS_PARALLELISM before any tokenizer imports
# This prevents warnings when tokenizers are used after forking
import os
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

from pathlib import Path
from typing import Dict, Optional

import chromadb
from anthropic import Anthropic
from dotenv import load_dotenv

import logging

# Import reranking, monitoring, caching, and hybrid search
from conductor.reranker import rerank_results
from conductor.monitoring import track_query, get_metrics_summary
from conductor.cache import cached_query, get_cache_stats
from conductor.hybrid_search import hybrid_search
from conductor.config import DEFAULT_DB_PATH, CHROMADB_URL, USE_VECS
from conductor.multi_query import generate_query_variations
from conductor.rank_fusion import fuse_chromadb_results

# Import vecs client if using Supabase
if USE_VECS:
    from conductor.vecs_client import query_vecs as _query_vecs_impl_vecs

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# System prompt for Claude
SYSTEM_PROMPT = """You are a Real Estate Archives Assistant. Answer based ONLY on the provided context.
Cite the specific date, channel, and agent name for every claim. If the information is not in the context, say "I don't have information about that in the archives."
"""


def _query_chromadb_impl(
    user_query: str,
    db_path: Optional[Path] = DEFAULT_DB_PATH,
    n_results: int = 5,
    where: Optional[Dict] = None,
    use_reranking: bool = True
) -> dict:
    """
    Query ChromaDB for similar sessions with optional metadata filtering.

    Args:
        user_query: Natural language query string
        db_path: Path to ChromaDB persistent storage directory (None if using HTTP client)
        n_results: Number of results to return
        where: Optional metadata filter dictionary (e.g., {"file_count": {"$gt": 0}})

    Returns:
        Dictionary with query results containing ids, documents, metadatas, distances
    """
    try:
        # Use vecs (Supabase pgvector) if DATABASE_URL is set
        if USE_VECS:
            # Convert ChromaDB-style filters to vecs format
            vecs_filters = {}
            if where:
                # Convert ChromaDB where clause to vecs filters
                # ChromaDB: {"date": {"$eq": "2024-01-01"}}
                # Vecs: {"date": {"$eq": "2024-01-01"}} (same format!)
                vecs_filters = where
            
            return _query_vecs_impl_vecs(
                query_text=user_query,
                n_results=n_results,
                filters=vecs_filters if vecs_filters else None
            )
        
        # Otherwise use ChromaDB
        # Initialize ChromaDB client
        # Use HTTP client if CHROMADB_URL is set (for Vercel/serverless)
        # Otherwise use PersistentClient (for local development)
        if CHROMADB_URL:
            # Parse URL to extract host and port
            from urllib.parse import urlparse
            parsed = urlparse(CHROMADB_URL)
            host = parsed.hostname or parsed.path
            port = parsed.port or 8000
            client = chromadb.HttpClient(host=host, port=port)
        else:
            if db_path is None:
                raise ValueError("db_path is required when CHROMADB_URL is not set")
            client = chromadb.PersistentClient(path=str(db_path))

        # Get collection
        collection = client.get_collection(name="conductor_sessions")

        # Build query parameters
        query_params = {
            "query_texts": [user_query],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        
        # Add metadata filter if provided
        if where is not None:
            query_params["where"] = where

        # Query ChromaDB (get more results for reranking)
        initial_n_results = n_results * 3 if use_reranking else n_results
        query_params["n_results"] = initial_n_results
        
        results = collection.query(**query_params)
        
        # Rerank results if enabled and we have documents
        if use_reranking and results.get("documents") and results["documents"][0]:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            
            reranked_docs, reranked_metas, reranked_scores = rerank_results(
                query=user_query,
                documents=documents,
                metadatas=metadatas,
                top_k=n_results
            )
            
            # Update results with reranked data
            results["documents"] = [reranked_docs]
            results["metadatas"] = [reranked_metas]
            # Update distances with reranked scores (inverted, as lower distance = better)
            results["distances"] = [[1.0 / (score + 0.001) for score in reranked_scores]]
            results["ids"] = [[meta.get("id", f"result_{i}") for i, meta in enumerate(reranked_metas)]]

        return results

    except Exception as e:
        logger.error(f"Failed to query ChromaDB: {e}")
        raise


def query_chromadb_deep_research(
    user_query: str,
    db_path: Optional[Path] = DEFAULT_DB_PATH,
    deep_research_n_results: int = 50,
    max_final_results: int = 40,
    where: Optional[Dict] = None,
    use_reranking: bool = True,
    num_query_variations: int = 7
) -> dict:
    """
    Perform exhaustive deep research using multi-query retrieval and RRF fusion.
    
    Generates multiple query variations (including media-specific), runs hybrid search
    for each, and fuses results using Reciprocal Rank Fusion for maximum coverage.
    
    Args:
        user_query: Original user query string
        db_path: Path to ChromaDB persistent storage directory
        deep_research_n_results: Number of results per query variation (default: 50)
        max_final_results: Maximum final results after RRF fusion (default: 40)
        where: Optional metadata filter dictionary
        use_reranking: Whether to rerank final results (default: True)
        num_query_variations: Number of query variations to generate (default: 7)
        
    Returns:
        Dictionary with fused query results containing ids, documents, metadatas, distances
    """
    logger.info(f"Starting deep research mode: {user_query[:50]}...")
    logger.debug(f"Parameters: n_results={deep_research_n_results}, max_final={max_final_results}, variations={num_query_variations}, reranking={use_reranking}")
    
    # Step 1: Generate query variations
    logger.info(f"Step 1/4: Generating {num_query_variations} query variations...")
    try:
        query_variations = generate_query_variations(user_query, num_variations=num_query_variations)
        logger.info(f"Generated {len(query_variations)} query variations")
        logger.debug(f"Query variations: {[q[:50] + '...' if len(q) > 50 else q for q in query_variations]}")
    except Exception as e:
        logger.error(f"Failed to generate query variations: {e}", exc_info=True)
        logger.warning("Falling back to single query")
        query_variations = [user_query]
    
    # Step 2: Run hybrid search for each query variation
    logger.info(f"Step 2/4: Running hybrid search for {len(query_variations)} query variations...")
    result_sets = []
    total_retrieved = 0
    
    for i, query_var in enumerate(query_variations, 1):
        logger.info(f"Query variation {i}/{len(query_variations)}: {query_var[:60]}...")
        
        try:
            # Use vecs if available, otherwise use hybrid search
            if USE_VECS:
                vecs_filters = where if where else {}
                hybrid_result = _query_vecs_impl_vecs(
                    query_text=query_var,
                    n_results=deep_research_n_results,
                    filters=vecs_filters if vecs_filters else None
                )
            else:
                # Run hybrid search (which combines vector + BM25 internally)
                hybrid_result = hybrid_search(
                    query_var,
                    db_path,
                    n_results=deep_research_n_results,
                    where=where,
                    semantic_weight=0.6,  # 60% vector, 40% BM25
                    keyword_weight=0.4
                )
            
            if hybrid_result.get("documents") and hybrid_result["documents"][0]:
                num_results = len(hybrid_result["documents"][0])
                result_sets.append(hybrid_result)
                total_retrieved += num_results
                logger.debug(f"  Retrieved {num_results} results from variation {i}")
            else:
                logger.warning(f"  No results from variation {i}")
        except Exception as e:
            logger.error(f"  Error retrieving results for variation {i}: {e}", exc_info=True)
            continue
    
    logger.info(f"Retrieved {total_retrieved} total results from {len(result_sets)} successful queries")
    
    if not result_sets:
        logger.warning("No results retrieved from any query variation")
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
    
    # Step 3: Fuse results using RRF
    logger.info(f"Step 3/4: Fusing {len(result_sets)} result sets using RRF...")
    try:
        fused_results = fuse_chromadb_results(
            result_sets,
            k=60,  # Standard RRF constant
            top_k=max_final_results
        )
        
        num_fused = len(fused_results.get('ids', [[]])[0])
        logger.info(f"RRF fusion complete: {num_fused} unique results from {total_retrieved} initial retrievals")
    except Exception as e:
        logger.error(f"Failed to fuse results with RRF: {e}", exc_info=True)
        # Fallback: use first result set
        logger.warning("Falling back to first result set")
        fused_results = result_sets[0] if result_sets else {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
    
    # Step 4: Apply final reranking if enabled
    if use_reranking and fused_results.get("documents") and fused_results["documents"][0]:
        logger.info(f"Step 4/4: Applying final reranking...")
        try:
            documents = fused_results["documents"][0]
            metadatas = fused_results["metadatas"][0]
            
            reranked_docs, reranked_metas, reranked_scores = rerank_results(
                query=user_query,  # Use original query for reranking
                documents=documents,
                metadatas=metadatas,
                top_k=max_final_results
            )
            
            # Update fused results with reranked data
            fused_results["documents"] = [reranked_docs]
            fused_results["metadatas"] = [reranked_metas]
            fused_results["distances"] = [[1.0 / (score + 0.001) for score in reranked_scores]]
            fused_results["ids"] = [[meta.get("id", f"result_{i}") for i, meta in enumerate(reranked_metas)]]
            
            logger.info(f"Final reranking complete: {len(reranked_docs)} results")
        except Exception as e:
            logger.error(f"Failed to rerank results: {e}", exc_info=True)
            logger.warning("Continuing with unfused results")
    
    logger.info(f"Deep research complete: {len(fused_results.get('ids', [[]])[0])} final results")
    return fused_results


@track_query
def query_chromadb(
    user_query: str,
    db_path: Optional[Path] = DEFAULT_DB_PATH,
    n_results: int = 5,
    where: Optional[Dict] = None,
    use_reranking: bool = True,
    use_cache: bool = True,
    use_hybrid: bool = False,
    use_deep_research: bool = False,
    deep_research_n_results: int = 50,
    max_final_results: int = 40
) -> dict:
    """
    Query ChromaDB with optional caching, hybrid search, reranking, and deep research.
    
    Args:
        user_query: Natural language query string
        db_path: Path to ChromaDB persistent storage directory
        n_results: Number of results to return (ignored if use_deep_research=True)
        where: Optional metadata filter dictionary
        use_reranking: Whether to rerank results (default: True)
        use_cache: Whether to use query caching (default: True, ignored if use_deep_research=True)
        use_hybrid: Whether to use hybrid search (default: False, ignored if use_deep_research=True)
        use_deep_research: Whether to use exhaustive deep research mode (default: False)
        deep_research_n_results: Results per query variation in deep research mode (default: 50)
        max_final_results: Maximum final results after RRF fusion (default: 40)
        
    Returns:
        Dictionary with query results
    """
    # Use deep research mode if requested (most comprehensive)
    if use_deep_research:
        return query_chromadb_deep_research(
            user_query,
            db_path,
            deep_research_n_results=deep_research_n_results,
            max_final_results=max_final_results,
            where=where,
            use_reranking=use_reranking
        )
    
    # Use hybrid search if requested
    if use_hybrid:
        return hybrid_search(user_query, db_path, n_results, where)
    
    # Use caching wrapper
    if use_cache:
        return cached_query(
            _query_chromadb_impl,
            user_query,
            db_path,
            n_results,
            where,
            use_cache=True
        )
    
    # Direct query without cache
    return _query_chromadb_impl(user_query, db_path, n_results, where, use_reranking)


def format_context(results: dict) -> str:
    """
    Format retrieved sessions into context string for Claude.

    Args:
        results: Query results from ChromaDB

    Returns:
        Formatted context string
    """
    if not results.get("documents") or not results["documents"][0]:
        return "No relevant context found."

    context_parts = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    for i, (doc, metadata) in enumerate(zip(documents, metadatas), 1):
        context_parts.append(f"<context id=\"{i}\">")
        context_parts.append(f"Date: {metadata.get('date', 'Unknown')}")
        context_parts.append(f"Channel: {metadata.get('channel', 'Unknown')}")
        context_parts.append(f"Start Time: {metadata.get('start_time', 'Unknown')}")
        context_parts.append(f"Message Count: {metadata.get('message_count', 'Unknown')}")
        context_parts.append(f"File Count: {metadata.get('file_count', 'Unknown')}")
        context_parts.append("")
        context_parts.append(doc)
        context_parts.append("</context>")
        context_parts.append("")

    return "\n".join(context_parts)


def query_claude(user_query: str, context: str, use_thinking: bool = False) -> str:
    """
    Query Claude with the user query and retrieved context.

    Args:
        user_query: Natural language query string
        context: Formatted context from retrieved sessions
        use_thinking: If True, enables thinking mode with chain-of-thought reasoning

    Returns:
        Claude's response text
    """
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Initialize Anthropic client
    client = Anthropic(api_key=api_key)

    # Construct user message with context
    user_message = f"""Context from archives:

{context}

Question: {user_query}"""

    # Enhanced system prompt for thinking mode
    thinking_system_prompt = """You are a Real Estate Operations Analyst analyzing administrative task completion times. 

Use structured thinking to analyze how long it takes admins to complete various jobs:

1. **Identify Task Requests**: Look for when tasks are requested (mentions, channel posts, direct requests)
2. **Identify Completions**: Find confirmation messages, "done" indicators, or completion signals
3. **Calculate Intervals**: Measure time between request and completion
4. **Categorize Tasks**: Group by task type (listing tasks, CRM management, file organization, etc.)
5. **Analyze Patterns**: Identify averages, ranges, and factors affecting timing
6. **Consider Context**: Account for urgency, complexity, workload, and follow-up patterns

Always cite specific dates, channels, and admin names. If information is incomplete, note the limitations.

Use chain-of-thought reasoning: break down complex questions into logical steps, consider multiple factors, and synthesize findings clearly."""

    try:
        # Prepare message parameters
        message_params = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 2048 if use_thinking else 1024,
            "system": thinking_system_prompt if use_thinking else SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        }
        
        # Add thinking mode if requested (using experimental thinking parameter if available)
        if use_thinking:
            # Note: Thinking mode may be available via model parameters or experimental features
            # This is a placeholder for when thinking mode becomes available in the API
            message_params["temperature"] = 0.3  # Lower temperature for more focused reasoning
        
        # Send to Claude
        message = client.messages.create(**message_params)

        # Extract text from response
        if message.content and len(message.content) > 0:
            # Claude returns a list of content blocks
            text_parts = []
            for block in message.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif isinstance(block, str):
                    text_parts.append(block)
            return "\n".join(text_parts)
        else:
            return "No response from Claude."

    except Exception as e:
        logger.error(f"Failed to query Claude: {e}")
        raise


def main(query: str, db_path: Optional[str] = None, filter_files: bool = False, use_reranking: bool = True, show_metrics: bool = False, use_cache: bool = True, use_hybrid: bool = False, use_thinking: bool = False, use_deep_research: bool = False, deep_research_n_results: int = 50, max_final_results: int = 40) -> None:
    """
    Query the semantic memory bank.

    Args:
        query: Natural language query string
        db_path: Optional path to ChromaDB database (default: /Users/noahdeskin/slack-vectoriezed-data)
        filter_files: If True, only return sessions with file attachments
        use_thinking: If True, enables thinking mode with chain-of-thought reasoning
    """
    logger.info(f"Query: {query}")
    if use_thinking:
        logger.info("Thinking mode enabled - using chain-of-thought reasoning")

    try:
        # Determine database path
        db_path_obj = Path(db_path) if db_path else DEFAULT_DB_PATH
        
        # Build metadata filter if requested
        where_filter = None
        if filter_files:
            where_filter = {"file_count": {"$gt": 0}}

        # Step 1: Query ChromaDB
        if use_deep_research:
            logger.info("Using exhaustive deep research mode...")
        logger.info("Querying ChromaDB...")
        results = query_chromadb(
            query,
            db_path=db_path_obj,
            where=where_filter,
            use_reranking=use_reranking,
            use_cache=use_cache,
            use_hybrid=use_hybrid,
            use_deep_research=use_deep_research,
            deep_research_n_results=deep_research_n_results,
            max_final_results=max_final_results
        )

        # Step 2: Format context
        logger.info("Formatting context...")
        context = format_context(results)

        # Step 3: Query Claude
        logger.info("Querying Claude...")
        if use_thinking:
            logger.info("Using thinking mode with Context7-guided reasoning")
        response = query_claude(query, context, use_thinking=use_thinking)

        # Step 4: Display response
        print("\n" + "=" * 80)
        print("RESPONSE:")
        print("=" * 80)
        print(response)
        print("=" * 80 + "\n")
        
        # Step 5: Show metrics if requested
        if show_metrics:
            metrics = get_metrics_summary()
            cache_stats = get_cache_stats()
            print("\n" + "=" * 80)
            print("METRICS:")
            print("=" * 80)
            print(f"Total Queries: {metrics['queries']['total']}")
            print(f"Success Rate: {metrics['queries']['success_rate']:.2%}")
            print(f"Avg Latency: {metrics['queries']['avg_latency_seconds']:.3f}s")
            print(f"P95 Latency: {metrics['queries']['p95_latency_seconds']:.3f}s")
            print(f"\nCache Stats:")
            print(f"  Total Entries: {cache_stats['total_entries']}")
            print(f"  Valid Entries: {cache_stats['valid_entries']}")
            print(f"  TTL: {cache_stats['ttl_seconds']}s")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Query failed: {e}")
        print(f"Error: {e}")
        import sys

        sys.exit(1)


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Query the semantic memory bank")
    parser.add_argument("query", help="Natural language query string")
    parser.add_argument("--db-path", help="Path to ChromaDB database (default: /Users/noahdeskin/slack-vectoriezed-data)")
    parser.add_argument("--filter-files", action="store_true", help="Only return sessions with file attachments")
    parser.add_argument("--no-reranking", action="store_true", help="Disable result reranking")
    parser.add_argument("--no-cache", action="store_true", help="Disable query caching")
    parser.add_argument("--hybrid", action="store_true", help="Use hybrid search (semantic + keyword)")
    parser.add_argument("--metrics", action="store_true", help="Show performance metrics")
    parser.add_argument("--thinking", action="store_true", help="Enable thinking mode with chain-of-thought reasoning (Context7-guided)")
    parser.add_argument("--deep-research", action="store_true", help="Use exhaustive deep research mode (multi-query + RRF fusion)")
    parser.add_argument("--deep-research-n-results", type=int, default=50, help="Results per query variation in deep research mode (default: 50)")
    parser.add_argument("--max-final-results", type=int, default=40, help="Maximum final results after RRF fusion (default: 40)")
    
    args = parser.parse_args()
    
    main(
        args.query,
        db_path=args.db_path,
        filter_files=args.filter_files,
        use_reranking=not args.no_reranking,
        use_cache=not args.no_cache,
        use_hybrid=args.hybrid,
        show_metrics=args.metrics,
        use_thinking=args.thinking,
        use_deep_research=args.deep_research,
        deep_research_n_results=args.deep_research_n_results,
        max_final_results=args.max_final_results
    )
