"""
CLI for querying the semantic memory bank.

Provides command-line interface for semantic search.
"""

import os
from pathlib import Path

import chromadb
from anthropic import Anthropic
from dotenv import load_dotenv

import logging

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


def query_chromadb(user_query: str, db_path: Path = Path("./conductor_db"), n_results: int = 5) -> dict:
    """
    Query ChromaDB for similar sessions.

    Args:
        user_query: Natural language query string
        db_path: Path to ChromaDB persistent storage directory
        n_results: Number of results to return

    Returns:
        Dictionary with query results containing ids, documents, metadatas, distances
    """
    try:
        # Initialize ChromaDB client
        client = chromadb.PersistentClient(path=str(db_path))

        # Get collection
        collection = client.get_collection(name="conductor_sessions")

        # Query ChromaDB
        results = collection.query(
            query_texts=[user_query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        return results

    except Exception as e:
        logger.error(f"Failed to query ChromaDB: {e}")
        raise


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


def query_claude(user_query: str, context: str) -> str:
    """
    Query Claude with the user query and retrieved context.

    Args:
        user_query: Natural language query string
        context: Formatted context from retrieved sessions

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

    try:
        # Send to Claude
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        )

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


def main(query: str) -> None:
    """
    Query the semantic memory bank.

    Args:
        query: Natural language query string
    """
    logger.info(f"Query: {query}")

    try:
        # Step 1: Query ChromaDB
        logger.info("Querying ChromaDB...")
        results = query_chromadb(query)

        # Step 2: Format context
        logger.info("Formatting context...")
        context = format_context(results)

        # Step 3: Query Claude
        logger.info("Querying Claude...")
        response = query_claude(query, context)

        # Step 4: Display response
        print("\n" + "=" * 80)
        print("RESPONSE:")
        print("=" * 80)
        print(response)
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Query failed: {e}")
        print(f"Error: {e}")
        import sys

        sys.exit(1)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m conductor.ask '<query>'")
        sys.exit(1)

    query = sys.argv[1]
    main(query)
