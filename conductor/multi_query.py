"""
Multi-query generation for exhaustive deep research.

Generates diverse query variations to maximize retrieval coverage,
including media-specific queries for images, videos, and audio.
"""

import os
import logging
from typing import List
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Template for generating multimodal-aware query variations
QUERY_GENERATION_TEMPLATE = """Generate 6-7 diverse search queries that comprehensively explore all aspects of: {query}

Consider that the database contains:
- Chat messages (text conversations)
- Images (with MLX-VLM descriptions stored as [IMAGE_PROCESSED: ...])
- Videos (with frame descriptions and audio transcriptions stored as [VIDEO_PROCESSED: ...])
- Audio files (with Whisper transcriptions stored as [AUDIO_PROCESSED: ...])

CRITICAL: If the query mentions videos, reels, video content, or visual media, you MUST include multiple video-specific queries.

Include these types of queries:
1. Original query (preserved as-is)
2. Expanded query (adds context, synonyms, related terms)
3. Specific aspects query (breaks down into components)
4. Alternative phrasings (different wording, same intent)
5. Related concepts (broader context, adjacent topics)
6. Media-specific queries (ALWAYS include if query mentions media):
   - Video-focused: "videos about X", "video content showing Y", "VIDEO_PROCESSED X", "video transcriptions about Z", "reels showing X", "agent videos about Y"
   - Image-focused: "images showing X", "photos of Y", "visual content about Z", "IMAGE_PROCESSED X"
   - Audio-focused: "audio discussing X", "recordings about Y", "transcriptions mentioning Z", "AUDIO_PROCESSED X"
7. Temporal/entity-focused (if mentions time/people/places)

IMPORTANT: When the query is about videos, include queries that search for:
- "[VIDEO_PROCESSED" markers (exact match)
- Video transcriptions and audio content
- Video metadata and descriptions
- Reel content and agent videos

Return ONLY the queries, one per line, without numbering or bullets. Start with the original query first."""


def generate_query_variations(user_query: str, num_variations: int = 7) -> List[str]:
    """
    Generate diverse query variations using Claude for exhaustive retrieval.
    
    Args:
        user_query: Original user query string
        num_variations: Number of query variations to generate (default: 7)
        
    Returns:
        List of query variation strings, starting with the original query
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = Anthropic(api_key=api_key)
    
    # Format the prompt
    prompt = QUERY_GENERATION_TEMPLATE.format(query=user_query)
    
    logger.debug(f"Generating {num_variations} query variations for query: {user_query[:100]}")
    
    try:
        logger.debug("Calling Claude API for query generation...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",  # Use Sonnet 4.5 for fast query generation
            max_tokens=500,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        
        logger.debug("Received response from Claude API")
        
        # Extract response text
        if message.content and len(message.content) > 0:
            text_parts = []
            for block in message.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif isinstance(block, str):
                    text_parts.append(block)
            response_text = "\n".join(text_parts)
            logger.debug(f"Extracted response text length: {len(response_text)} characters")
        else:
            logger.warning("No response content from Claude for query generation")
            return [user_query]  # Fallback to original query only
        
        # Parse queries from response (one per line)
        queries = []
        raw_lines = response_text.strip().split("\n")
        logger.debug(f"Parsing {len(raw_lines)} lines from response")
        
        for line_num, line in enumerate(raw_lines, 1):
            line = line.strip()
            # Skip empty lines and numbered/bulleted lines
            if line and not line.startswith(("#", "-", "*", "1.", "2.", "3.", "4.", "5.", "6.", "7.")):
                # Remove any leading numbers or bullets if present
                cleaned = line.lstrip("0123456789.-* ").strip()
                if cleaned:
                    queries.append(cleaned)
                    logger.debug(f"  Parsed query {len(queries)}: {cleaned[:60]}...")
        
        # Ensure original query is first
        if queries and queries[0] != user_query:
            logger.debug("Original query not first, inserting at beginning")
            queries.insert(0, user_query)
        elif not queries:
            logger.warning("No queries parsed from response, using original query only")
            queries = [user_query]
        
        # Limit to requested number of variations
        if len(queries) > num_variations:
            logger.debug(f"Limiting queries from {len(queries)} to {num_variations}")
            queries = queries[:num_variations]
        
        logger.info(f"Generated {len(queries)} query variations for: {user_query[:50]}...")
        for i, q in enumerate(queries, 1):
            logger.debug(f"  Variation {i}: {q[:80]}...")
        return queries
        
    except Exception as e:
        logger.error(f"Failed to generate query variations: {e}", exc_info=True)
        # Fallback to original query only
        return [user_query]

