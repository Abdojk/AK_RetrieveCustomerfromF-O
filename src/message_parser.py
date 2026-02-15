"""Extract customer fields from transcribed text using rule-based parsing."""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when customer fields cannot be extracted from text."""


@dataclass
class CustomerFields:
    """Validated customer fields extracted from voice message."""

    customer_account: str
    organization_name: str
    customer_group_id: str


# Patterns for each field (case-insensitive)
_ACCOUNT_PATTERNS = [
    r"(?:customer\s+)?(?:account|id|ID)\s+([A-Za-z0-9]+)",
    r"account\s+(?:number\s+)?([A-Za-z0-9]+)",
]

_NAME_PATTERNS = [
    r"(?:organization|company|customer)?\s*name\s+(.+?)(?:,|\.|group|$)",
    r"(?:called|named)\s+(.+?)(?:,|\.|group|$)",
]

_GROUP_PATTERNS = [
    r"(?:customer\s+)?group\s+(?:number\s+|id\s+)?(\d+)",
]

# Word-to-digit mapping for common spoken numbers
_WORD_DIGITS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "twenty": "20", "thirty": "30", "forty": "40",
    "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80",
    "ninety": "90", "hundred": "100",
}


def _normalize_number(text: str) -> str:
    """Convert spoken number words to digits (e.g., 'eighty' -> '80')."""
    text = text.strip().lower()
    if text.isdigit():
        return text
    return _WORD_DIGITS.get(text, text)


def _find_match(text: str, patterns: list[str]) -> str | None:
    """Try multiple regex patterns and return the first match."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_customer_fields(text: str) -> CustomerFields:
    """Extract customer account, organization name, and group ID from text.

    Expects the voice message to contain keywords like 'account', 'name',
    and 'group' followed by their values.

    Example inputs that work:
        - "Create customer account AK005, name Abdo Khoury, group 80"
        - "Account AK005 name Abdo Khoury group 80"
        - "Customer ID AK005 called Abdo Khoury group eighty"

    Args:
        text: Transcribed text from a voice message.

    Returns:
        CustomerFields dataclass with the three required fields.

    Raises:
        ParseError: If any of the three fields cannot be extracted.
    """
    logger.info("Parsing transcription: %s", text)

    account = _find_match(text, _ACCOUNT_PATTERNS)
    name = _find_match(text, _NAME_PATTERNS)
    group_raw = _find_match(text, _GROUP_PATTERNS)

    missing = []
    if not account:
        missing.append("account ID")
    if not name:
        missing.append("organization name")
    if not group_raw:
        missing.append("group number")

    if missing:
        raise ParseError(
            f"Could not extract: {', '.join(missing)}.\n\n"
            "Please say your message like this:\n"
            '"Account AK005, name Abdo Khoury, group 80"'
        )

    group = _normalize_number(group_raw)

    fields = CustomerFields(
        customer_account=account,
        organization_name=name,
        customer_group_id=group,
    )
    logger.info("Extracted fields: %s", fields)
    return fields
