"""
Prompt system using Context7 best practices.

Uses system prompts to guide Claude's behavior for vector database search.
Combines query understanding and search agent instructions in a single system prompt.
"""

import os
from typing import Optional
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# System prompt for Real Estate Archives Search Agent
# Combines query refinement logic and search agent instructions
SYSTEM_PROMPT_SEARCH_AGENT = """You are a Real Estate Archives Search Agent with expertise in analyzing administrative tasks, agent communications, and operational patterns.

**Your Role:**
- Understand user queries naturally, expanding implicit references (e.g., "agents" -> "real estate agents", "listings" -> "property listings")
- Identify key concepts, entities (people, actions, objects), and relationships
- Analyze retrieved context to answer questions accurately and comprehensively

**Query Understanding:**
When interpreting user queries:
1. Analyze the user's intent and identify key concepts
2. Expand implicit references to make queries more searchable
3. Consider relevant synonyms and related terms
4. Focus on entities: people (agents, admins), actions (requests, completions), objects (listings, deals, files)
5. Preserve the original meaning while understanding context

**Task Analysis:**
When analyzing administrative tasks and operations:
1. Identify task requests (mentions, channel posts, direct requests)
2. Identify completions (confirmation messages, "done" indicators, completion signals)
3. Calculate intervals between request and completion
4. Categorize tasks (listing tasks, CRM management, file organization, etc.)
5. Analyze patterns (averages, ranges, factors affecting timing)
6. Consider context (urgency, complexity, workload, follow-up patterns)

**Requirements:**
- Always cite specific dates, channels, and admin/agent names
- If information is incomplete, note the limitations
- Use chain-of-thought reasoning for complex questions
- Break down complex questions into logical steps
- Synthesize findings clearly
- Answer based ONLY on the provided context from the archives
- If information is not in the context, say "I don't have information about that in the archives."
"""


# Legacy refine_query function removed - query understanding is now handled by system prompt
# The system prompt guides Claude to naturally understand and interpret queries

def format_user_message(query: str, context: str) -> str:
    """
    Format user message with query and context.
    
    Simple format without XML structure - system prompt handles instructions.
    
    Args:
        query: User query string
        context: Retrieved context from vector database
        
    Returns:
        Formatted user message string
    """
    return f"""Context from archives:

{context}

Question: {query}"""


def query_claude_with_system_prompt(
    query: str,
    context: str,
    use_thinking: bool = False,
    system_prompt: Optional[str] = None
) -> str:
    """
    Query Claude with system prompt and user message.
    
    Uses system prompt to guide Claude's behavior instead of XML-formatted prompts.
    
    Args:
        query: User query string
        context: Retrieved context from vector database
        use_thinking: Enable thinking mode
        system_prompt: Optional custom system prompt (defaults to SYSTEM_PROMPT_SEARCH_AGENT)
        
    Returns:
        Claude's response text
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = Anthropic(api_key=api_key)
    
    # Use provided system prompt or default
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT_SEARCH_AGENT
    
    # Format user message
    user_message = format_user_message(query, context)
    
    message_params = {
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 2048 if use_thinking else 1024,
        "temperature": 0.3 if use_thinking else 0.7,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": user_message,
            }
        ],
    }
    
    message = client.messages.create(**message_params)
    
    # Extract response
    if message.content and len(message.content) > 0:
        text_parts = []
        for block in message.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(text_parts)
    else:
        return "No response from Claude."


# Legacy function names for backward compatibility (deprecated)
def create_db_search_prompt(refined_query: str, context: str) -> str:
    """
    Legacy function - use format_user_message() instead.
    
    Deprecated: This function is kept for backward compatibility but will be removed.
    """
    return format_user_message(refined_query, context)


def query_claude_with_xml_prompt(xml_prompt: str, use_thinking: bool = False) -> str:
    """
    Legacy function - use query_claude_with_system_prompt() instead.
    
    Deprecated: This function is kept for backward compatibility but will be removed.
    Attempts to extract query and context from XML prompt for migration.
    """
    import re
    # Try to extract query and context from XML format
    query_match = re.search(r"<query>\s*(.*?)\s*</query>", xml_prompt, re.DOTALL)
    context_match = re.search(r"<context>\s*(.*?)\s*</context>", xml_prompt, re.DOTALL)
    
    if query_match and context_match:
        query = query_match.group(1).strip()
        context = context_match.group(1).strip()
        return query_claude_with_system_prompt(query, context, use_thinking=use_thinking)
    else:
        # Fallback: treat entire prompt as user message (not ideal but works)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        client = Anthropic(api_key=api_key)
        message_params = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 2048 if use_thinking else 1024,
            "temperature": 0.3 if use_thinking else 0.7,
            "system": SYSTEM_PROMPT_SEARCH_AGENT,
            "messages": [
                {
                    "role": "user",
                    "content": xml_prompt,
                }
            ],
        }
        message = client.messages.create(**message_params)
        if message.content and len(message.content) > 0:
            text_parts = []
            for block in message.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif isinstance(block, str):
                    text_parts.append(block)
            return "\n".join(text_parts)
        else:
            return "No response from Claude."

