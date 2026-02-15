"""Extract customer fields from natural language text using OpenAI GPT."""

import json
import logging
from dataclasses import dataclass

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a data extraction assistant for a Dynamics 365 Finance & Operations system.
Your job is to extract exactly three fields from a user's voice message about creating a new customer.

The three required fields are:
1. CustomerAccount - A short alphanumeric identifier (e.g., "AK001", "CUST042"). If the user says something like "account AK001" or "customer ID AK001", extract "AK001".
2. OrganizationName - The full name of the customer/company/organization (e.g., "Abdo Khoury", "Contoso Ltd").
3. CustomerGroupId - A numeric group identifier (e.g., "80", "10", "20"). If the user says "group 80" or "customer group eighty", extract "80".

You MUST respond with ONLY a valid JSON object in this exact format, with no additional text:
{"CustomerAccount": "...", "OrganizationName": "...", "CustomerGroupId": "..."}

If you cannot confidently extract ALL THREE fields from the message, respond with:
{"error": "Could not extract [list missing fields]. Please state your customer account ID, organization name, and customer group number."}"""


class ParseError(Exception):
    """Raised when customer fields cannot be extracted from text."""


@dataclass
class CustomerFields:
    """Validated customer fields extracted from voice message."""

    customer_account: str
    organization_name: str
    customer_group_id: str


def extract_customer_fields(text: str, api_key: str) -> CustomerFields:
    """Extract customer account, organization name, and group ID from text.

    Args:
        text: Free-form transcribed text from a voice message.
        api_key: OpenAI API key.

    Returns:
        CustomerFields dataclass with the three required fields.

    Raises:
        ParseError: If GPT cannot extract all three fields or returns invalid JSON.
    """
    client = OpenAI(api_key=api_key)

    try:
        logger.info("Sending transcription to GPT for field extraction...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
    except (APIError, APIConnectionError, RateLimitError) as exc:
        logger.error("GPT API error: %s", exc)
        raise ParseError(f"Field extraction failed: {exc}") from exc

    raw = response.choices[0].message.content.strip()
    logger.info("GPT response: %s", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("GPT returned invalid JSON: %s", raw)
        raise ParseError(
            "Could not parse the response. Please try again with a clearer message."
        ) from exc

    if "error" in data:
        raise ParseError(data["error"])

    account = str(data.get("CustomerAccount", "")).strip()
    name = str(data.get("OrganizationName", "")).strip()
    group = str(data.get("CustomerGroupId", "")).strip()

    missing = []
    if not account:
        missing.append("CustomerAccount")
    if not name:
        missing.append("OrganizationName")
    if not group:
        missing.append("CustomerGroupId")

    if missing:
        raise ParseError(
            f"Could not extract: {', '.join(missing)}. "
            "Please state your customer account ID, organization name, "
            "and customer group number."
        )

    fields = CustomerFields(
        customer_account=account,
        organization_name=name,
        customer_group_id=group,
    )
    logger.info("Extracted fields: %s", fields)
    return fields
