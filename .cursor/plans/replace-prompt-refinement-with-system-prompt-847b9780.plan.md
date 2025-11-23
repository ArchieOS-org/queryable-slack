<!-- 847b9780-ba6d-4fc8-a776-5e98d7b4da18 f840378f-eee4-40c3-bbe7-c2b24aea0695 -->
# Exhaustive Multimodal Deep Research System for 3 Years of Data

## Overview

Implement the most extremely thorough database search possible for 3 years of multimodal data (10,088 sessions containing chat messages, images, videos, and audio files) by combining multiple advanced retrieval techniques: multi-query generation (5-7 variations including media-specific queries), hybrid search (vector + BM25), Reciprocal Rank Fusion, 50+ results per query variation, and an enhanced system prompt that automatically provides comprehensive analytical responses across all content types.

## Current State

- **Database**: 10,088 sessions (3 years of Slack data)
- **Content Types**: 
  - Chat messages (text)
  - Images (MLX-VLM descriptions stored as `[IMAGE_PROCESSED: ...]`)
  - Videos (Frame descriptions + audio transcriptions stored as `[VIDEO_PROCESSED: ...]`)
  - Audio files (Whisper transcriptions stored as `[AUDIO_PROCESSED: ...]`)
- **Current Limitations**:
  - Single query retrieval with `n_results=5`
  - Basic system prompt lacks multimodal awareness and deep analysis instructions
  - No query expansion to specifically target visual or audio content
  - Maximum ChromaDB retrievable: 10,000 per query

## Architecture: Exhaustive Search Strategy

```mermaid
graph TD
    A[User Query] --> B[Generate 5-7 Query Variations]
    B --> C1[Query 1: Original]
    B --> C2[Query 2: Expanded]
    B --> C3[Query 3: Specific Aspects]
    B --> C4[Query 4: Alternative Phrasing]
    B --> C5[Query 5: Related Concepts]
    B --> C6[Query 6: Media-Specific (Image/Video/Audio)]
    B --> C7[Query 7: Temporal/Entity Focus]
    
    C1 --> D1[Hybrid Search<br/>Vector + BM25<br/>n_results=50]
    C2 --> D2[Hybrid Search<br/>Vector + BM25<br/>n_results=50]
    C3 --> D3[Hybrid Search<br/>Vector + BM25<br/>n_results=50]
    C4 --> D4[Hybrid Search<br/>Vector + BM25<br/>n_results=50]
    C5 --> D5[Hybrid Search<br/>Vector + BM25<br/>n_results=50]
    C6 --> D6[Hybrid Search<br/>Vector + BM25<br/>n_results=50]
    C7 --> D7[Hybrid Search<br/>Vector + BM25<br/>n_results=50]
    
    D1 --> E[Reciprocal Rank Fusion<br/>Combine 14 Result Sets]
    D2 --> E
    D3 --> E
    D4 --> E
    D5 --> E
    D6 --> E
    D7 --> E
    
    E --> F[Deduplicate & Rank<br/>Top 40-50 Unique Sessions]
    F --> G[Final Reranking]
    G --> H[System Prompt<br/>Multimodal Analysis Instructions]
    H --> I[Comprehensive Research Response]
    
    style E fill:#ccffcc
    style F fill:#ccffcc
    style H fill:#ccffcc
```

## Implementation Plan

### 1. Create Multi-Query Generator (`conductor/multi_query.py`)

- Generate 5-7 diverse query variations using Claude
- **Query Types**:
  - Original query (preserved)
  - Expanded query (adds context, synonyms, related terms)
  - Specific aspects query (breaks down into components)
  - Alternative phrasings (different wording, same intent)
  - **Media-Specific Queries**:
    - Image-focused: "images showing X", "photos of Y", "visual content about Z"
    - Video-focused: "videos about X", "video content showing Y", "transcriptions of video Z"
    - Audio-focused: "audio discussing X", "recordings about Y", "transcriptions mentioning Z"
  - Temporal/entity-focused (if mentions time/people/places)
- **Template**: "Generate 6-7 diverse search queries that comprehensively explore all aspects of: {query}. Consider that the database contains chat messages, images (with descriptions), videos (with descriptions and transcriptions), and audio files (with transcriptions). Include original, expanded, specific, alternative, related, **media-specific** (if applicable), and entity-focused variations."

### 2. Implement Reciprocal Rank Fusion (`conductor/rank_fusion.py`)

- RRF algorithm: `score += 1 / (rank + k)` where k=60
- Efficient deduplication using session ID
- Handle large result sets (500-700 initial retrievals)
- Return top 40-50 unique sessions containing relevant multimodal content

### 3. Enhance Hybrid Search (`conductor/hybrid_search.py`)

- Ensure hybrid search works with multi-query
- Combine vector similarity (60%) + BM25 keyword (40%)
- Apply to each query variation to capture both semantic meaning (good for descriptions) and exact keywords (good for transcriptions)

### 4. Update Query Function (`conductor/ask.py`)

- Add `use_deep_research: bool = True` (default True)
- Add `deep_research_n_results: int = 50` (per query variation)
- Add `max_final_results: int = 40` (after RRF fusion)
- **Workflow**:
  - Generate 5-7 query variations (including media-aware queries)
  - For each variation:
    - Run hybrid search (vector + BM25)
    - Retrieve n_results=50 from each method
  - Apply RRF to combine all 10-14 result sets
  - Deduplicate while preserving ranking
  - Return top 40-50 unique, highly relevant sessions

### 5. Update System Prompt (`conductor/prompt_refiner.py`)

- Enhance `SYSTEM_PROMPT_SEARCH_AGENT` for **Exhaustive Multimodal Analysis**
- **Add Sections**:
  - **Automatic Deep Analysis**: Always provide comprehensive analytical responses.
  - **Multimodal Awareness**: 
    - Explicitly instruct to look for and cite `[IMAGE_PROCESSED: ...]`, `[VIDEO_PROCESSED: ...]`, and `[AUDIO_PROCESSED: ...]` markers.
    - Distinguish between text messages and media content in analysis.
  - **Research-Level Depth**: Analyze patterns, trends, individual behaviors, comparisons, temporal changes, exceptions across ALL media types.
  - **Structured Output**: Clear sections, subsections, bullet points, numbered references.
  - **Comprehensive Coverage**: Synthesize ALL retrieved contexts (40-50 sessions).
  - **Reference Format**: `[N] Context ID X, Date: YYYY-MM-DD, Channel: Z, Agent: Name, Media Type: [Chat/Image/Video/Audio]`
  - **Analysis Requirements**: 
    - "What does the visual evidence show?" (for images/video)
    - "What does the audio evidence confirm?" (for audio/video)
    - Compare what is said (chat) vs. what is shown (media).

### 6. Update API Endpoint (`web_api.py`)

- Add `use_deep_research: bool = True` (default True)
- Pass deep research parameters to query function
- Update response model to include retrieval stats (query variations, total retrievals, media types found)

### 7. Update CLI Tools (`chat.py`, `chat_fullscreen.py`)

- Support deep research mode with same parameters
- Display retrieval statistics including breakdown of media types found

## Key Features

**Multimodal Multi-Query Generation**:

- Generates queries specifically targeting visual and audio descriptions to ensure media is retrieved.

**Massive Hybrid Retrieval**:

- 500-700 initial retrievals per search.
- Hybrid search captures both semantic descriptions (e.g., "graph of sales") and exact transcription keywords.

**Multimodal System Prompt**:

- explicitly trained to recognize and analyze `[IMAGE_PROCESSED]`, `[VIDEO_PROCESSED]`, `[AUDIO_PROCESSED]` tags.
- Provides holistic analysis combining text, visual, and audio evidence.

## Benefits

- **Total Recall**: Minimizes chance of missing key evidence whether it's in a text, image, video, or audio file.
- **Holistic Analysis**: Connects what was written with what was shown or spoken.
- **Research Depth**: Provides the most thorough possible answer from 3 years of archives.

## Files to Create/Modify

1. `conductor/multi_query.py` - NEW: Generate 5-7 multimodal-aware query variations
2. `conductor/rank_fusion.py` - NEW: RRF implementation
3. `conductor/ask.py` - Update: Exhaustive multimodal deep research mode
4. `conductor/hybrid_search.py` - Update/Check: Ensure compatibility
5. `conductor/prompt_refiner.py` - Update: Multimodal-aware system prompt
6. `web_api.py` - Update: Deep research parameters
7. `conductor/chat.py` - Update: Support deep research
8. `conductor/chat_fullscreen.py` - Update: Support deep research

### To-dos

- [ ] Create conductor/multi_query.py with query variation generation using Claude
- [ ] Create conductor/rank_fusion.py implementing Reciprocal Rank Fusion algorithm
- [ ] Update conductor/ask.py to support multi-query retrieval with 20+ results and RRF
- [ ] Update SYSTEM_PROMPT_SEARCH_AGENT in prompt_refiner.py to automatically provide deep analytical responses with structured format
- [ ] Update web_api.py to support deep research mode (default enabled)
- [ ] Update chat.py and chat_fullscreen.py to support deep research