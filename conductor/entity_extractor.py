"""
Entity extraction for Conductor.

Extracts structured entities from real estate conversations using:
- LLM-based extraction with Claude tool_use for comprehensive extraction
- Pattern-based extraction for structured entities (addresses, prices, MLS IDs)
- Hybrid approach combining both methods

Entity Types:
- PERSON: Agent names, client names, admin names
- ADDRESS: Property addresses
- DEAL: Transaction references, deal names
- COMPANY: Brokerages, vendors, companies
- LISTING_ID: MLS numbers, internal listing IDs
- PRICE: Dollar amounts
- DATE_REFERENCE: Closing dates, deadlines, specific dates
"""

import os
import re
import logging
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Entity type definitions
ENTITY_TYPES = {
    "PERSON": "Names of people (agents, clients, admins)",
    "ADDRESS": "Property addresses (street number + name)",
    "DEAL": "Transaction references or deal names",
    "COMPANY": "Brokerages, vendors, companies",
    "LISTING_ID": "MLS numbers, internal listing IDs",
    "PRICE": "Dollar amounts and prices",
    "DATE_REFERENCE": "Specific dates mentioned (closings, deadlines)",
}


class ExtractedEntity(BaseModel):
    """A single extracted entity with metadata."""

    entity_type: str = Field(..., description="Type of entity (PERSON, ADDRESS, etc.)")
    value: str = Field(..., description="Raw extracted value")
    normalized_value: str = Field(..., description="Standardized/normalized form")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    context: Optional[str] = Field(None, description="Surrounding context where found")


class ExtractionResult(BaseModel):
    """Result of entity extraction."""

    entities: List[ExtractedEntity] = Field(default_factory=list)
    method: str = Field(..., description="Extraction method used: llm, pattern, hybrid")
    text_length: int = Field(..., description="Length of input text")


# Tool definition for Claude entity extraction
ENTITY_EXTRACTION_TOOL = {
    "name": "extract_entities",
    "description": "Extracts all entities from a real estate conversation",
    "input_schema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "description": "List of extracted entities",
                "items": {
                    "type": "object",
                    "properties": {
                        "entity_type": {
                            "type": "string",
                            "description": "Type: PERSON, ADDRESS, DEAL, COMPANY, LISTING_ID, PRICE, DATE_REFERENCE",
                            "enum": list(ENTITY_TYPES.keys()),
                        },
                        "value": {
                            "type": "string",
                            "description": "Raw extracted value",
                        },
                        "normalized_value": {
                            "type": "string",
                            "description": "Standardized form (e.g., 'John Smith' not 'john')",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence score 0.0 to 1.0",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "context": {
                            "type": "string",
                            "description": "Brief context where entity appears",
                        },
                    },
                    "required": ["entity_type", "value", "normalized_value", "confidence"],
                },
            }
        },
        "required": ["entities"],
    },
}


def extract_entities_llm(
    text: str,
    client: Optional[Anthropic] = None,
    max_text_length: int = 8000,
) -> List[ExtractedEntity]:
    """
    Use Claude with tool_use for comprehensive entity extraction.

    Args:
        text: Text to extract entities from
        client: Anthropic client (created if not provided)
        max_text_length: Maximum text length to process

    Returns:
        List of extracted entities
    """
    if not text or not text.strip():
        return []

    # Get or create client
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, skipping LLM extraction")
            return []
        client = Anthropic(api_key=api_key)

    # Truncate if needed
    truncated_text = text[:max_text_length] if len(text) > max_text_length else text

    prompt = f"""Extract ALL entities from this real estate conversation.

Entity types to find:
- PERSON: Names of people (agents, clients, admins, team members)
- ADDRESS: Property addresses (normalize to "Number StreetName" format)
- DEAL: Transaction references, deal names, property references
- COMPANY: Brokerages, vendors, companies mentioned
- LISTING_ID: MLS numbers, internal IDs (e.g., "MLS W123456")
- PRICE: Dollar amounts (normalize to "$X,XXX" format)
- DATE_REFERENCE: Specific dates mentioned (closings, deadlines)

For PERSON entities:
- Extract first names, last names, or full names
- Include nicknames and short names (EJ, DJ, TJ)
- Normalize to proper case: "EJ" not "ej", "Mary Smith" not "mary smith"

For ADDRESS entities:
- Use flexible matching: "123 Main St" or "123 Main"
- Normalize format: "Number StreetName"

Text to analyze:
<document>
{truncated_text}
</document>

Use the extract_entities tool to return all found entities with confidence scores."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            tools=[ENTITY_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_entities"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract tool result
        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_entities":
                entities_data = block.input.get("entities", [])
                entities = []
                for e in entities_data:
                    try:
                        entities.append(ExtractedEntity(**e))
                    except Exception as parse_err:
                        logger.warning(f"Failed to parse entity: {e}, error: {parse_err}")
                logger.info(f"LLM extraction found {len(entities)} entities")
                return entities

        logger.warning("No tool_use response from Claude")
        return []

    except Exception as e:
        logger.error(f"LLM entity extraction failed: {e}")
        return []


def extract_entities_pattern(text: str) -> List[ExtractedEntity]:
    """
    Fast pattern-based extraction for structured entities.

    Uses regex patterns for high-confidence extraction of:
    - Addresses (Number + Street)
    - Prices ($X,XXX)
    - MLS IDs (MLS + ID)
    - Dates (various formats)

    Args:
        text: Text to extract entities from

    Returns:
        List of extracted entities
    """
    if not text or not text.strip():
        return []

    entities = []

    # ADDRESS: Number + Street Name (flexible)
    # Matches: "123 Main St", "1234 Seymour Ave", "156 O'Donoghue"
    address_pattern = re.compile(
        r"\b(\d{1,5}\s+[A-Z][a-z']+(?:\s+[A-Z][a-z']+)*)"
        r"(?:\s+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Ln|Lane|Ct|Court|Way|Pl|Place))?"
        r"\.?\b",
        re.IGNORECASE,
    )
    for match in address_pattern.finditer(text):
        value = match.group(0).strip()
        # Normalize: Title case the street name part
        parts = value.split(maxsplit=1)
        if len(parts) == 2:
            normalized = f"{parts[0]} {parts[1].title()}"
        else:
            normalized = value.title()
        entities.append(
            ExtractedEntity(
                entity_type="ADDRESS",
                value=value,
                normalized_value=normalized.rstrip("."),
                confidence=0.85,
                context=text[max(0, match.start() - 20) : match.end() + 20],
            )
        )

    # PRICE: Dollar amounts ($X,XXX or $X.XM/K)
    price_pattern = re.compile(
        r"\$[\d,]+(?:\.\d{1,2})?(?:\s*[MKmk])?|\$\d+(?:\.\d+)?\s*(?:million|thousand)",
        re.IGNORECASE,
    )
    for match in price_pattern.finditer(text):
        value = match.group(0).strip()
        entities.append(
            ExtractedEntity(
                entity_type="PRICE",
                value=value,
                normalized_value=value.upper().replace(" ", ""),
                confidence=0.95,
                context=text[max(0, match.start() - 20) : match.end() + 20],
            )
        )

    # LISTING_ID: MLS numbers (MLS W123456, #123456, etc.)
    mls_pattern = re.compile(r"\b(?:MLS\s*)?[#]?[A-Z]?\d{5,8}\b", re.IGNORECASE)
    for match in mls_pattern.finditer(text):
        value = match.group(0).strip()
        # Only include if it looks like an ID (not just a random number)
        if re.search(r"[A-Z]|MLS|#", value, re.IGNORECASE) or len(value) >= 6:
            entities.append(
                ExtractedEntity(
                    entity_type="LISTING_ID",
                    value=value,
                    normalized_value=value.upper().replace(" ", ""),
                    confidence=0.8,
                    context=text[max(0, match.start() - 20) : match.end() + 20],
                )
            )

    # DATE_REFERENCE: Various date formats
    date_pattern = re.compile(
        r"\b(?:"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"  # 01/15/2024, 1-15-24
        r"|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?"  # Jan 15, 2024
        r"|"
        r"\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?(?:,?\s+\d{4})?"  # 15th of January
        r")\b",
        re.IGNORECASE,
    )
    for match in date_pattern.finditer(text):
        value = match.group(0).strip()
        entities.append(
            ExtractedEntity(
                entity_type="DATE_REFERENCE",
                value=value,
                normalized_value=value,
                confidence=0.9,
                context=text[max(0, match.start() - 20) : match.end() + 20],
            )
        )

    # PERSON: Capitalized names (using improved pattern from query_classifier)
    # This is a simpler pattern - LLM is better for person extraction
    person_pattern = re.compile(
        r"\b(?:"
        r"[A-Z]{1,3}(?:['']?s)?(?:\s+[A-Z][a-z]*)?"  # Initials: EJ, DJ, TJ
        r"|"
        r"[A-Z][a-z]+(?:\s+[A-Z](?:[a-z]+)?)*"  # Standard: Mary, Mary Smith
        r")\b",
        re.UNICODE,
    )
    common_words = {
        "What", "Who", "How", "When", "Where", "Why", "Which",
        "The", "A", "An", "Is", "Are", "Was", "Were", "Do", "Does",
        "Can", "Could", "Would", "Should", "May", "Might", "Will",
        "Show", "Tell", "Find", "Get", "List", "Give", "Let", "See",
        "All", "Any", "Some", "Most", "Many", "Few", "Each", "Every",
        "And", "Or", "But", "Not", "For", "With", "About", "From", "To",
        "Just", "Also", "Very", "Really", "Actually", "Basically",
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
        "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        "Hello", "Hi", "Hey", "Thanks", "Thank", "Please", "Sorry",
        "Good", "Great", "Nice", "Sure", "Yes", "No", "Ok", "Okay",
    }

    for match in person_pattern.finditer(text):
        value = match.group(0).strip()
        # Clean possessive
        clean_value = re.sub(r"['']?s$", "", value)
        if clean_value and clean_value not in common_words and len(clean_value) >= 2:
            entities.append(
                ExtractedEntity(
                    entity_type="PERSON",
                    value=value,
                    normalized_value=clean_value,
                    confidence=0.6,  # Lower confidence for pattern-based person extraction
                    context=text[max(0, match.start() - 20) : match.end() + 20],
                )
            )

    logger.info(f"Pattern extraction found {len(entities)} entities")
    return entities


def extract_entities(
    text: str,
    use_llm: bool = True,
    client: Optional[Anthropic] = None,
) -> ExtractionResult:
    """
    Hybrid entity extraction combining LLM and pattern-based methods.

    Strategy:
    1. Always run pattern extraction (fast, high-confidence for structured data)
    2. Optionally run LLM extraction (slower, better for names/context)
    3. Merge and deduplicate results

    Args:
        text: Text to extract entities from
        use_llm: Whether to use LLM extraction (default True)
        client: Optional Anthropic client

    Returns:
        ExtractionResult with merged entities
    """
    if not text or not text.strip():
        return ExtractionResult(entities=[], method="none", text_length=0)

    # Step 1: Pattern extraction (always run)
    pattern_entities = extract_entities_pattern(text)

    # Step 2: LLM extraction (optional)
    llm_entities = []
    if use_llm:
        llm_entities = extract_entities_llm(text, client=client)

    # Step 3: Merge and deduplicate
    all_entities = pattern_entities + llm_entities

    # Deduplicate by (entity_type, normalized_value.lower())
    seen: Dict[tuple, ExtractedEntity] = {}
    for entity in all_entities:
        key = (entity.entity_type, entity.normalized_value.lower())
        if key not in seen:
            seen[key] = entity
        else:
            # Keep the one with higher confidence
            if entity.confidence > seen[key].confidence:
                seen[key] = entity

    unique_entities = list(seen.values())

    # Determine method
    if use_llm and llm_entities:
        method = "hybrid"
    else:
        method = "pattern"

    logger.info(
        f"Entity extraction complete: {len(unique_entities)} unique entities "
        f"(pattern: {len(pattern_entities)}, llm: {len(llm_entities)})"
    )

    return ExtractionResult(
        entities=unique_entities,
        method=method,
        text_length=len(text),
    )


def group_entities_by_type(entities: List[ExtractedEntity]) -> Dict[str, List[str]]:
    """
    Group entities by type for metadata storage.

    Args:
        entities: List of extracted entities

    Returns:
        Dictionary mapping entity type to list of normalized values
    """
    grouped: Dict[str, List[str]] = {}
    for entity in entities:
        if entity.entity_type not in grouped:
            grouped[entity.entity_type] = []
        if entity.normalized_value not in grouped[entity.entity_type]:
            grouped[entity.entity_type].append(entity.normalized_value)
    return grouped


def get_entity_list(entities: List[ExtractedEntity], entity_type: str) -> List[str]:
    """
    Get list of normalized values for a specific entity type.

    Args:
        entities: List of extracted entities
        entity_type: Type to filter by (PERSON, ADDRESS, etc.)

    Returns:
        List of unique normalized values for that type
    """
    values = []
    seen = set()
    for entity in entities:
        if entity.entity_type == entity_type:
            key = entity.normalized_value.lower()
            if key not in seen:
                seen.add(key)
                values.append(entity.normalized_value)
    return values
