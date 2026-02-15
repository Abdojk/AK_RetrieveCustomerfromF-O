"""End-to-end local test of the WhatsApp → Whisper → GPT → D365 pipeline.

Simulates what happens when a voice message arrives, without needing
Twilio/ngrok. Tests each stage independently.
"""

import os
import sys
import logging
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from src.speech_to_text import transcribe_audio, TranscriptionError
from src.message_parser import extract_customer_fields, ParseError
from src.auth import D365Authenticator
from src.api_client import D365ApiClient
from src.customer_service import create_customer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_pipeline")


def test_gpt_extraction(api_key: str) -> None:
    """Stage 2: Test GPT field extraction with simulated transcription text."""
    print("\n--- STAGE 2: GPT Field Extraction ---")
    simulated_transcription = "Create customer AK099, name Test Customer, group 80"
    print(f"   Input text: '{simulated_transcription}'")

    try:
        fields = extract_customer_fields(simulated_transcription, api_key)
        print(f"   Account:  {fields.customer_account}")
        print(f"   Name:     {fields.organization_name}")
        print(f"   Group:    {fields.customer_group_id}")
        print("   RESULT: PASS")
        return fields
    except ParseError as exc:
        print(f"   RESULT: FAIL — {exc}")
        return None


def test_d365_auth() -> D365ApiClient:
    """Stage 3: Test D365 authentication."""
    print("\n--- STAGE 3: D365 Authentication ---")
    try:
        authenticator = D365Authenticator(
            tenant_id=os.environ["D365_TENANT_ID"],
            client_id=os.environ["D365_CLIENT_ID"],
            client_secret=os.environ["D365_CLIENT_SECRET"],
            environment_url=os.environ["D365_ENVIRONMENT_URL"],
        )
        token = authenticator.get_access_token()
        client = D365ApiClient(
            environment_url=os.environ["D365_ENVIRONMENT_URL"],
            access_token=token,
        )
        print("   RESULT: PASS — Authenticated to D365")
        return client
    except Exception as exc:
        print(f"   RESULT: FAIL — {exc}")
        return None


def test_d365_create(client: D365ApiClient) -> None:
    """Stage 4: Test customer creation in D365."""
    print("\n--- STAGE 4: D365 Customer Creation ---")
    unique_id = f"AKTEST{int(time.time()) % 100000}"
    try:
        created = create_customer(
            client=client,
            customer_account=unique_id,
            organization_name="Pipeline Test Customer",
            customer_group_id="80",
        )
        account = created.get("CustomerAccount", "?")
        name = created.get("OrganizationName", "?")
        group = created.get("CustomerGroupId", "?")
        print(f"   Created: Account={account}, Name={name}, Group={group}")
        print("   RESULT: PASS")
    except Exception as exc:
        print(f"   RESULT: FAIL — {exc}")


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key == "your_openai_api_key":
        print("OPENAI_API_KEY not set. Cannot test.")
        sys.exit(1)

    print("=" * 55)
    print("  END-TO-END PIPELINE TEST")
    print("  Whisper (skipped) → GPT → D365 Auth → D365 Create")
    print("=" * 55)

    # Stage 1: Whisper — skip (no real audio file to send)
    print("\n--- STAGE 1: Whisper Transcription ---")
    print("   (Skipped — no audio file; using simulated text)")
    print("   RESULT: SKIPPED")

    # Stage 2: GPT extraction
    fields = test_gpt_extraction(api_key)
    if not fields:
        print("\nPipeline stopped at Stage 2.")
        return

    # Stage 3: D365 auth
    client = test_d365_auth()
    if not client:
        print("\nPipeline stopped at Stage 3.")
        return

    # Stage 4: D365 create
    test_d365_create(client)

    print("\n" + "=" * 55)
    print("  PIPELINE TEST COMPLETE")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
