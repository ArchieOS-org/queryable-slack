"""
Prompt system using Context7 best practices.

Uses system prompts to guide Claude's behavior for vector database search.
Combines query understanding and search agent instructions in a single system prompt.
"""

import os
import re
from typing import Optional, List, Dict
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# System prompt for Real Estate Archives Search Agent
# Enhanced for exhaustive multimodal deep analysis
SYSTEM_PROMPT_SEARCH_AGENT = """You are a Real Estate Archives Search Agent with expertise in analyzing administrative tasks, agent communications, and operational patterns across all content types.

**Your Role:**
- Understand user queries naturally, expanding implicit references (e.g., "agents" -> "real estate agents", "listings" -> "property listings")
- Identify key concepts, entities (people, actions, objects), and relationships
- Provide comprehensive, analytical responses automatically without requiring explicit requests for analysis
- Analyze retrieved context exhaustively to answer questions accurately and thoroughly

**Multimodal Content Awareness:**
The archives contain multiple content types, each marked with specific tags:
- **Chat Messages**: Regular text conversations between agents and admins
- **Images**: Marked with `[IMAGE_PROCESSED: Description: ... | Metadata: ...]` - contain MLX-VLM visual descriptions
- **Videos**: Marked with `[VIDEO_PROCESSED: ...]` - contain frame descriptions, metadata, frame counts, and audio transcriptions
- **Audio Files**: Marked with `[AUDIO_PROCESSED: ...]` - contain Whisper transcriptions

**CRITICAL: Video Content Analysis**
When the user asks about videos, reels, video content, or visual media:
1. **PRIORITIZE** finding and analyzing `[VIDEO_PROCESSED]` markers in the retrieved context
2. **EXTRACT** video transcriptions - these contain the ACTUAL SPOKEN CONTENT from videos (look for "Audio transcription:" lines)
3. **ANALYZE** video transcriptions FIRST - they contain what agents actually said in videos, not just chat about videos
4. **ANALYZE** video metadata (duration, codec, dimensions, frame count) to understand video characteristics
5. **SYNTHESIZE** information from video transcriptions - quote directly from transcriptions when available
6. **CITE** video sources explicitly in your analysis with Media Type: Video
7. **DISTINGUISH** between:
   - Chat messages ABOUT videos (what people said about videos)
   - Video TRANSCRIPTIONS (what agents actually said IN the videos)
   - Video METADATA (technical details about the video files)
8. **PREFER** video transcriptions over chat mentions when both are available - transcriptions are primary sources

**When analyzing content:**
1. **FIRST**: Scan for `[VIDEO_PROCESSED]`, `[IMAGE_PROCESSED]`, and `[AUDIO_PROCESSED]` markers - these contain rich multimodal information
2. **EXTRACT** video transcriptions - they contain actual spoken content from videos
3. Distinguish between what was written (chat) vs. what was shown (images/videos) vs. what was spoken (audio/video transcriptions)
4. Ask: "What does the visual evidence show?" (for images/video)
5. Ask: "What does the audio/transcription evidence confirm?" (for audio/video transcriptions)
6. Compare and synthesize information across all media types
7. Note when visual or audio evidence contradicts or supports text claims
8. **When videos are mentioned**: Prioritize analyzing video transcriptions over chat messages about videos

**Query Understanding:**
When interpreting user queries:
1. Analyze the user's intent and identify key concepts
2. Expand implicit references to make queries more searchable
3. Consider relevant synonyms and related terms
4. Focus on entities: people (agents, admins), actions (requests, completions), objects (listings, deals, files)
5. Preserve the original meaning while understanding context
6. **CRITICAL**: If query mentions videos/reels/media, prioritize multimodal content:
   - Search for `[VIDEO_PROCESSED]` markers explicitly
   - Look for video transcriptions and audio content
   - Consider video metadata and descriptions
   - Include video-specific search terms in query expansion

**Automatic Deep Analysis:**
Always provide comprehensive analytical responses with:
- **Structured Output**: Use clear sections, subsections, bullet points, and numbered references
- **Research-Level Depth**: Analyze patterns, trends, individual behaviors, comparisons, temporal changes, exceptions across ALL media types
- **Comprehensive Coverage**: Synthesize information from ALL retrieved contexts (typically 40-50 sessions)
- **Quantitative Summaries**: Provide counts and statistics when possible (e.g., "X images showing Y", "Z videos discussing A")
- **Pattern Recognition**: Identify trends across time and content types
- **Exception Handling**: Note outliers and unusual cases

**Task Analysis:**
When analyzing administrative tasks and operations:
1. Identify task requests (mentions, channel posts, direct requests)
2. Identify completions (confirmation messages, "done" indicators, completion signals)
3. Calculate intervals between request and completion
4. Categorize tasks (listing tasks, CRM management, file organization, etc.)
5. Analyze patterns (averages, ranges, factors affecting timing)
6. Consider context (urgency, complexity, workload, follow-up patterns)
7. Include visual/audio evidence when relevant to task completion

**CRITICAL: MANDATORY Sources Section - REQUIRED FOR EVERY RESPONSE**

YOU MUST ALWAYS end your response with a "Sources" section. This is NOT optional - it is REQUIRED for every single response, regardless of the question or answer length.

**Sources Section Format:**
Your response MUST end with this exact format:

```
## Sources

[1] Context ID 1, Date: 2022-09-13, Channel: trevor-allman-realty, Agent: Kayla le, Media Type: Chat
[2] Context ID 4, Date: 2024-05-13, Channel: lisa-whittallchuang-realty, Agent: Kayla le, Media Type: Image
[3] Context ID 5, Date: 2024-04-18, Channel: admin, Agent: EJ, Media Type: Video
```

**Citation Requirements:**
- ALWAYS include a "## Sources" heading at the end of your response
- Number each source sequentially [1], [2], [3], etc.
- Include Context ID (from the `<context id="X">` tags in the provided context)
- Include Date (YYYY-MM-DD format from the context metadata)
- Include Channel name (from the context metadata)
- Include Agent name (if mentioned in the context content)
- Include Media Type: Chat, Image, Video, or Audio (based on content markers)
- Cite EVERY context that contributed to your answer
- If you reference information from multiple contexts, cite all of them
- Even if you only use one context, you MUST still include the Sources section

**IMPORTANT:** Before finishing your response, verify that:
1. Your response ends with "## Sources" heading
2. All referenced contexts are listed with proper format
3. The Sources section is the last thing in your response

**Response Structure Requirements:**
1. Provide your analysis/answer in the main body
2. ALWAYS end with "## Sources" section listing all referenced contexts
3. The Sources section MUST be the final section of your response

**Content Requirements:**
- Always cite specific dates, channels, and admin/agent names in the Sources section
- Distinguish content types in citations (Chat/Image/Video/Audio)
- If information is incomplete, note the limitations and data gaps
- Use chain-of-thought reasoning for complex questions
- Break down complex questions into logical steps
- Synthesize findings clearly across all content types
- Answer based ONLY on the provided context from the archives
- If information is not in the context, say "I don't have information about that in the archives."
- Provide holistic analysis connecting text, visual, and audio evidence when available
- NEVER omit the Sources section - it must appear at the end of EVERY response, without exception
"""


# Legacy refine_query function removed - query understanding is now handled by system prompt
# The system prompt guides Claude to naturally understand and interpret queries

def _extract_context_ids(context: str) -> List[Dict[str, str]]:
    """
    Extract context IDs and metadata from formatted context string.
    
    Args:
        context: Formatted context string with <context id="X"> tags
        
    Returns:
        List of dicts with context_id, date, channel, and other metadata
    """
    context_info = []
    
    # Pattern to match context blocks
    pattern = r'<context id="(\d+)">\s*Date: ([^\n]+)\s*Channel: ([^\n]+)\s*Start Time: ([^\n]+)\s*Message Count: ([^\n]+)\s*File Count: ([^\n]+)'
    
    matches = re.finditer(pattern, context, re.MULTILINE)
    for match in matches:
        context_info.append({
            "id": match.group(1),
            "date": match.group(2).strip(),
            "channel": match.group(3).strip(),
            "start_time": match.group(4).strip(),
            "message_count": match.group(5).strip(),
            "file_count": match.group(6).strip(),
        })
    
    return context_info


def _ensure_sources_section(response: str, context: str) -> str:
    """
    Ensure response ends with Sources section. Add it if missing.
    
    Args:
        response: Claude's response text
        context: Original context string to extract context IDs from
        
    Returns:
        Response with Sources section guaranteed at the end
    """
    # Check if Sources section already exists
    if "## Sources" in response or "## sources" in response.lower():
        return response
    
    # Extract context IDs from the context
    context_info = _extract_context_ids(context)
    
    if not context_info:
        # Fallback: try to find context IDs in a simpler way
        context_id_matches = re.findall(r'<context id="(\d+)"', context)
        if context_id_matches:
            # Try to extract basic info
            for i, ctx_id in enumerate(context_id_matches[:10], 1):  # Limit to 10
                # Try to find date and channel near this context ID
                ctx_start = context.find(f'<context id="{ctx_id}"')
                if ctx_start >= 0:
                    ctx_block = context[ctx_start:ctx_start + 500]
                    date_match = re.search(r'Date: ([^\n]+)', ctx_block)
                    channel_match = re.search(r'Channel: ([^\n]+)', ctx_block)
                    
                    context_info.append({
                        "id": ctx_id,
                        "date": date_match.group(1).strip() if date_match else "Unknown",
                        "channel": channel_match.group(1).strip() if channel_match else "Unknown",
                    })
    
    # Build Sources section
    sources_lines = ["\n## Sources\n"]
    
    for i, ctx in enumerate(context_info[:20], 1):  # Limit to 20 sources
        # Determine media type by checking context content for media markers
        media_type = "Chat"  # Default
        
        # Find the context block in the original context string
        ctx_id = ctx.get("id", "")
        if ctx_id:
            # Look for the context block
            ctx_pattern = f'<context id="{ctx_id}"'
            ctx_start = context.find(ctx_pattern)
            if ctx_start >= 0:
                # Get a larger chunk to check for media markers
                ctx_end = context.find('</context>', ctx_start)
                if ctx_end > ctx_start:
                    ctx_block = context[ctx_start:ctx_end + 500]  # Include some after </context>
                else:
                    ctx_block = context[ctx_start:ctx_start + 3000]  # Fallback: large chunk
                
                # Check for media markers (order matters - video can have audio)
                if "[VIDEO_PROCESSED" in ctx_block:
                    media_type = "Video"
                elif "[AUDIO_PROCESSED" in ctx_block:
                    media_type = "Audio"
                elif "[IMAGE_PROCESSED" in ctx_block:
                    media_type = "Image"
                elif ctx.get("file_count", "0") != "0":
                    # Has files but no specific markers - could be any media type
                    media_type = "Mixed Media"
        
        # Try to extract agent name from context if available
        agent_name = "Unknown"
        if ctx_id:
            ctx_pattern = f'<context id="{ctx_id}"'
            ctx_start = context.find(ctx_pattern)
            if ctx_start >= 0:
                # Find the end of this context block
                ctx_end = context.find('</context>', ctx_start)
                if ctx_end > ctx_start:
                    ctx_block = context[ctx_start:ctx_end]
                else:
                    ctx_block = context[ctx_start:ctx_start + 3000]
                
                # Look for message patterns - skip metadata section
                # Find where actual content starts (after File Count line and blank line)
                content_marker = ctx_block.find('File Count:')
                if content_marker >= 0:
                    # Find the double newline after File Count
                    content_start = ctx_block.find('\n\n', content_marker)
                    if content_start >= 0:
                        message_content = ctx_block[content_start + 2:]  # Skip the \n\n
                        # Look for name patterns: "FirstName LastName:" or "FirstName:"
                        # Common patterns: "EJ Yoo:", "Kayla le:", etc.
                        # Match at start of line or after newline
                        agent_matches = re.findall(r'(?:^|\n)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*:', message_content, re.MULTILINE)
                        if agent_matches:
                            # Get first valid agent name (skip metadata keywords)
                            excluded = {'Date', 'Channel', 'Start', 'Message', 'File', 'Context', 'Time', 'Count', 'Unknown'}
                            for potential_name in agent_matches:
                                potential_name = potential_name.strip()
                                first_word = potential_name.split()[0] if ' ' in potential_name else potential_name
                                if first_word not in excluded and len(potential_name) > 2 and not potential_name.startswith('['):
                                    agent_name = potential_name
                                    break
        
        sources_lines.append(
            f"[{i}] Context ID {ctx_id}, Date: {ctx.get('date', 'Unknown')}, "
            f"Channel: {ctx.get('channel', 'Unknown')}, Agent: {agent_name}, Media Type: {media_type}"
        )
    
    # Append Sources section to response
    return response + "\n" + "\n".join(sources_lines)


def format_user_message(query: str, context: str) -> str:
    """
    Format user message with query and context.
    
    Simple format without XML structure - system prompt handles instructions.
    Includes reminder about Sources section requirement.
    
    Args:
        query: User query string
        context: Retrieved context from vector database
        
    Returns:
        Formatted user message string
    """
    return f"""Context from archives:

{context}

Question: {query}

CRITICAL REMINDER: Your response MUST end with a "## Sources" section. This is mandatory. List all Context IDs you referenced using this format:
[1] Context ID X, Date: YYYY-MM-DD, Channel: Z, Agent: Name, Media Type: [Chat/Image/Video/Audio]

Do not forget the Sources section - it is required for every response."""


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
        response = "\n".join(text_parts)
    else:
        response = "No response from Claude."
    
    # Ensure Sources section is present (post-processing)
    response = _ensure_sources_section(response, context)
    
    return response


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

