"""
Query classification for routing to appropriate analysis modes.

Classifies user queries to determine:
- Query type (factual, analytical, comparative, etc.)
- Whether extended thinking should be enabled
- Entities mentioned for targeted retrieval
- Analysis dimensions (strengths, weaknesses, patterns)
"""

from typing import Literal, List, Optional
from pydantic import BaseModel
import re
import logging

logger = logging.getLogger(__name__)

QueryType = Literal["factual", "analytical", "comparative", "temporal", "behavioral"]


class QueryClassification(BaseModel):
    """Classification result for a user query."""
    query_type: QueryType
    requires_extended_thinking: bool
    suggested_budget_tokens: int
    entities_mentioned: List[str]
    analysis_dimensions: List[str]
    confidence: float = 1.0


# Patterns that indicate analytical queries requiring deep reasoning
ANALYTICAL_PATTERNS = [
    # Strengths/weaknesses analysis
    r"strength|weakness|pros?\s+and\s+cons?|advantage|disadvantage",
    # Performance evaluation
    r"good\s+at|bad\s+at|excel|struggle|capable|incapable",
    # Comparison queries
    r"compare|versus|vs\.?|difference|similar|better|worse",
    # Pattern/behavior analysis
    r"pattern|trend|behavior|habit|style|tendency|typically",
    # Performance metrics
    r"performance|effective|efficient|productive|how\s+well",
    # Assessment/evaluation
    r"assess|evaluate|review|analyze|examination",
    # Quality judgments
    r"quality|reliable|consistent|inconsistent",
]

# Patterns for comparative queries
COMPARATIVE_PATTERNS = [
    r"compare|versus|vs\.?|between",
    r"better\s+than|worse\s+than|more\s+than|less\s+than",
    r"difference|similar|same\s+as",
]

# Patterns for temporal queries
TEMPORAL_PATTERNS = [
    r"over\s+time|history|evolution|progress|change",
    r"before|after|since|until|during",
    r"trend|growth|decline|improvement",
    r"recent|latest|last\s+\w+|this\s+\w+",
]

# Patterns for behavioral queries
BEHAVIORAL_PATTERNS = [
    r"how\s+does|how\s+do|what\s+does|what\s+do",
    r"behavior|approach|method|style|way\s+of",
    r"respond|handle|manage|deal\s+with",
]


def extract_entities(query: str) -> List[str]:
    """
    Extract potential entity names from query.

    Looks for capitalized words that likely represent:
    - Person names (EJ, Kayla, Lisa, Mary Smith)
    - Short names/initials (EJ, DJ, TJ, AJ)
    - Possessive forms (EJ's, EJs)
    - Property addresses (156 Seymour)
    - Company names
    """
    entities = []

    # Pattern for flexible name matching (handles initials and possessives)
    # Matches:
    # - Short uppercase names: "EJ", "DJ", "TJ", "AJ"
    # - Possessives: "EJ's", "EJs"
    # - Multi-word names: "Mary Smith", "EJ Smith"
    # - Standard names: "Kayla", "Lisa"
    name_pattern = re.compile(
        r"\b(?:"
        r"[A-Z]{1,3}(?:['']?s)?(?:\s+[A-Z][a-z]*)?"  # Initials (EJ, DJ) + optional possessive + optional surname
        r"|"
        r"[A-Z][a-z]+(?:\s+[A-Z](?:[a-z]+)?)*"  # Standard names (Mary, Mary Smith, Mary J)
        r")\b",
        re.UNICODE
    )
    matches = name_pattern.findall(query)

    # Filter out common words that happen to be capitalized
    common_words = {
        'What', 'Who', 'How', 'When', 'Where', 'Why', 'Which',
        'The', 'A', 'An', 'Is', 'Are', 'Was', 'Were', 'Do', 'Does',
        'Can', 'Could', 'Would', 'Should', 'May', 'Might',
        'Show', 'Tell', 'Find', 'Get', 'List', 'Give',
        'All', 'Any', 'Some', 'Most', 'Many', 'Few',
        'And', 'Or', 'But', 'Not', 'For', 'With', 'About',
    }

    for match in matches:
        # Clean possessive suffix for comparison but keep original
        clean_match = re.sub(r"['']?s$", "", match)
        # Skip common words
        if clean_match not in common_words:
            # Normalize: strip possessive suffix for entity name
            normalized = clean_match.strip()
            if normalized:
                entities.append(normalized)

    # Also look for address-like patterns
    address_pattern = r'\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    address_matches = re.findall(address_pattern, query)
    entities.extend(address_matches)

    # Deduplicate while preserving order
    seen = set()
    unique_entities = []
    for e in entities:
        if e.lower() not in seen:
            seen.add(e.lower())
            unique_entities.append(e)

    return unique_entities


def extract_analysis_dimensions(query: str) -> List[str]:
    """
    Determine what dimensions of analysis the query is asking for.
    """
    query_lower = query.lower()
    dimensions = []

    # Strengths dimension
    if re.search(r'strength|good\s+at|excel|capable|advantage|positive', query_lower):
        dimensions.append("strengths")

    # Weaknesses dimension
    if re.search(r'weakness|bad\s+at|struggle|incapable|disadvantage|negative|issue|problem', query_lower):
        dimensions.append("weaknesses")

    # Patterns dimension
    if re.search(r'pattern|trend|behavior|habit|tendency|typically|usually', query_lower):
        dimensions.append("patterns")

    # Communication dimension
    if re.search(r'communicat|respond|message|reply|email|chat', query_lower):
        dimensions.append("communication")

    # Performance dimension
    if re.search(r'performance|effective|efficient|productive|quality', query_lower):
        dimensions.append("performance")

    # Relationships dimension
    if re.search(r'work\s+with|team|collaborat|relationship|partner', query_lower):
        dimensions.append("relationships")

    return dimensions if dimensions else ["general"]


def classify_query(query: str) -> QueryClassification:
    """
    Classify a user query to determine processing mode.

    Returns QueryClassification with:
    - query_type: The category of query
    - requires_extended_thinking: Whether to enable Claude's extended thinking
    - suggested_budget_tokens: Budget for extended thinking
    - entities_mentioned: Detected entity names
    - analysis_dimensions: What aspects to analyze
    """
    query_lower = query.lower()

    # Extract entities first
    entities = extract_entities(query)

    # Determine query type based on patterns
    is_analytical = any(re.search(p, query_lower) for p in ANALYTICAL_PATTERNS)
    is_comparative = any(re.search(p, query_lower) for p in COMPARATIVE_PATTERNS)
    is_temporal = any(re.search(p, query_lower) for p in TEMPORAL_PATTERNS)
    is_behavioral = any(re.search(p, query_lower) for p in BEHAVIORAL_PATTERNS)

    # Determine query type
    if is_comparative:
        query_type: QueryType = "comparative"
    elif is_analytical:
        query_type = "analytical"
    elif is_temporal:
        query_type = "temporal"
    elif is_behavioral:
        query_type = "behavioral"
    else:
        query_type = "factual"

    # Determine if extended thinking is needed
    # NOTE: Disabled for now due to Vercel 60s timeout - analytical prompt alone provides good results
    # Re-enable when using longer timeout or streaming
    requires_extended_thinking = False  # Was: query_type in ("analytical", "comparative", "behavioral")

    # Budget tokens based on complexity (balanced for Vercel 60s timeout)
    if query_type == "analytical" and len(entities) > 0:
        # Person/entity analysis needs more thinking
        budget_tokens = 6000  # Reduced from 10000 for faster response
    elif query_type == "comparative":
        # Comparisons need moderate thinking
        budget_tokens = 5000  # Reduced from 8000
    elif requires_extended_thinking:
        # Other complex queries
        budget_tokens = 4000  # Reduced from 6000
    else:
        budget_tokens = 0

    # Extract analysis dimensions
    dimensions = extract_analysis_dimensions(query)

    # Calculate confidence based on pattern matches
    pattern_match_count = sum([is_analytical, is_comparative, is_temporal, is_behavioral])
    confidence = min(1.0, 0.5 + (pattern_match_count * 0.2) + (len(entities) * 0.1))

    classification = QueryClassification(
        query_type=query_type,
        requires_extended_thinking=requires_extended_thinking,
        suggested_budget_tokens=budget_tokens,
        entities_mentioned=entities,
        analysis_dimensions=dimensions,
        confidence=confidence,
    )

    logger.info(
        f"Query classified: type={query_type}, "
        f"extended_thinking={requires_extended_thinking}, "
        f"entities={entities}, "
        f"dimensions={dimensions}"
    )

    return classification


def is_entity_focused_query(classification: QueryClassification) -> bool:
    """Check if query is focused on a specific entity."""
    return (
        len(classification.entities_mentioned) > 0 and
        classification.query_type in ("analytical", "behavioral", "comparative")
    )


def get_primary_entity(classification: QueryClassification) -> Optional[str]:
    """Get the primary entity being queried about."""
    if classification.entities_mentioned:
        return classification.entities_mentioned[0]
    return None
