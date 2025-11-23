"""
CLI for querying the semantic memory bank.

Provides command-line interface for semantic search.
"""

import os
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
from conductor.config import DEFAULT_DB_PATH

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
    db_path: Path = DEFAULT_DB_PATH,
    n_results: int = 5,
    where: Optional[Dict] = None,
    use_reranking: bool = True
) -> dict:
    """
    Query ChromaDB for similar sessions with optional metadata filtering.

    Args:
        user_query: Natural language query string
        db_path: Path to ChromaDB persistent storage directory
        n_results: Number of results to return
        where: Optional metadata filter dictionary (e.g., {"file_count": {"$gt": 0}})

    Returns:
        Dictionary with query results containing ids, documents, metadatas, distances
    """
    try:
        # Initialize ChromaDB client
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


@track_query
def query_chromadb(
    user_query: str,
    db_path: Path = DEFAULT_DB_PATH,
    n_results: int = 5,
    where: Optional[Dict] = None,
    use_reranking: bool = True,
    use_cache: bool = True,
    use_hybrid: bool = False
) -> dict:
    """
    Query ChromaDB with optional caching, hybrid search, and reranking.
    
    Args:
        user_query: Natural language query string
        db_path: Path to ChromaDB persistent storage directory
        n_results: Number of results to return
        where: Optional metadata filter dictionary
        use_reranking: Whether to rerank results (default: True)
        use_cache: Whether to use query caching (default: True)
        use_hybrid: Whether to use hybrid search (default: False)
        
    Returns:
        Dictionary with query results
    """
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


def main(query: str, db_path: Optional[str] = None, filter_files: bool = False, use_reranking: bool = True, show_metrics: bool = False, use_cache: bool = True, use_hybrid: bool = False, use_thinking: bool = False) -> None:
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
        logger.info("Querying ChromaDB...")
        results = query_chromadb(
            query,
            db_path=db_path_obj,
            where=where_filter,
            use_reranking=use_reranking,
            use_cache=use_cache,
            use_hybrid=use_hybrid
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
    
    args = parser.parse_args()
    
    main(
        args.query,
        db_path=args.db_path,
        filter_files=args.filter_files,
        use_reranking=not args.no_reranking,
        use_cache=not args.no_cache,
        use_hybrid=args.hybrid,
        show_metrics=args.metrics,
        use_thinking=args.thinking
    )
