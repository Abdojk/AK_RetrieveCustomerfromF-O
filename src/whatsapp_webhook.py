"""Flask webhook server for WhatsApp voice message integration with D365 F&O."""

import logging
import os

import requests as http_requests
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from src.auth import D365Authenticator
from src.api_client import D365ApiClient
from src.customer_service import create_customer
from src.speech_to_text import transcribe_audio, TranscriptionError
from src.message_parser import extract_customer_fields, ParseError

logger = logging.getLogger(__name__)

USAGE_INSTRUCTIONS = (
    "Welcome to the D365 F&O Customer Creator!\n\n"
    "Send a *voice message* describing the customer you want to create.\n\n"
    "Include:\n"
    "- Customer account ID (e.g. AK001)\n"
    "- Organization name (e.g. Abdo Khoury)\n"
    "- Customer group number (e.g. 80)\n\n"
    'Example: "Create customer AK005, name Abdo Khoury, group 80"'
)


class WhatsAppConfig:
    """Configuration holder for WhatsApp webhook dependencies."""

    def __init__(self) -> None:
        self.twilio_account_sid: str = os.environ["TWILIO_ACCOUNT_SID"]
        self.twilio_auth_token: str = os.environ["TWILIO_AUTH_TOKEN"]
        self.twilio_whatsapp_number: str = os.environ["TWILIO_WHATSAPP_NUMBER"]
        self.openai_api_key: str = os.environ["OPENAI_API_KEY"]
        self.d365_tenant_id: str = os.environ["D365_TENANT_ID"]
        self.d365_client_id: str = os.environ["D365_CLIENT_ID"]
        self.d365_client_secret: str = os.environ["D365_CLIENT_SECRET"]
        self.d365_environment_url: str = os.environ["D365_ENVIRONMENT_URL"]
        self.request_validator = RequestValidator(self.twilio_auth_token)


def create_app(
    config: WhatsAppConfig | None = None,
    skip_validation: bool = False,
) -> Flask:
    """Create and configure the Flask application.

    Args:
        config: Optional pre-built config. If None, reads from environment.
        skip_validation: If True, skip Twilio signature validation (dev only).

    Returns:
        Configured Flask app instance.
    """
    app = Flask(__name__)

    if config is None:
        config = WhatsAppConfig()
    app.config["WHATSAPP_CONFIG"] = config
    app.config["SKIP_VALIDATION"] = skip_validation

    @app.route("/webhook", methods=["GET"])
    def webhook_verify() -> Response:
        """Handle Twilio webhook verification."""
        return Response("OK", status=200)

    @app.route("/webhook", methods=["POST"])
    def webhook_incoming() -> Response:
        """Handle incoming WhatsApp messages from Twilio."""
        cfg: WhatsAppConfig = app.config["WHATSAPP_CONFIG"]

        # Step 1: Validate Twilio request signature
        if app.config["SKIP_VALIDATION"]:
            logger.debug("Twilio signature validation skipped (dev mode).")
        elif not _validate_twilio_request(cfg.request_validator, request):
            logger.warning("Invalid Twilio signature — rejecting request.")
            return Response("Forbidden", status=403)

        sender = request.form.get("From", "unknown")
        body = request.form.get("Body", "")
        logger.info("Incoming WhatsApp message from %s", sender)
        logger.info("Message body: %s", body if body else "(empty — likely voice/media)")

        try:
            return _process_voice_message(cfg, request)
        except Exception as exc:
            logger.exception("Unhandled error processing WhatsApp message: %s", exc)
            return _make_twiml_reply(
                "Something went wrong while processing your message. "
                "Please try again. If the problem persists, contact an administrator."
            )

    return app


def _process_voice_message(cfg: WhatsAppConfig, req) -> Response:
    """Process an incoming WhatsApp message through the full voice pipeline.

    Separated from the route handler so that a top-level except can
    guarantee a TwiML reply even on unexpected errors.
    """
    # Step 2: Check for voice message (media attachment)
    num_media = int(req.form.get("NumMedia", "0"))
    if num_media < 1:
        logger.info("Text-only message received — sending usage instructions.")
        return _make_twiml_reply(USAGE_INSTRUCTIONS)

    media_url = req.form.get("MediaUrl0", "")
    media_type = req.form.get("MediaContentType0", "")
    logger.info("Media received: type=%s, url=%s", media_type, media_url)

    # Step 3: Download audio from Twilio
    try:
        audio_data = _download_audio(
            media_url, cfg.twilio_account_sid, cfg.twilio_auth_token
        )
    except RuntimeError as exc:
        logger.error("Audio download failed: %s", exc)
        return _make_twiml_reply(
            "Failed to download your voice message. Please try again."
        )

    # Step 4: Transcribe audio via Whisper
    try:
        transcription = transcribe_audio(audio_data, cfg.openai_api_key)
    except TranscriptionError as exc:
        logger.error("Transcription failed: %s", exc)
        return _make_twiml_reply(
            "Could not transcribe your voice message. "
            "Please try again with a clearer recording."
        )

    logger.info("Transcription: %s", transcription)

    # Step 5: Extract customer fields via GPT
    try:
        fields = extract_customer_fields(transcription, cfg.openai_api_key)
    except ParseError as exc:
        logger.warning("Field extraction failed: %s", exc)
        return _make_twiml_reply(str(exc))

    # Step 6: Authenticate to D365 and create customer
    try:
        client = _get_d365_client(cfg)
        created = create_customer(
            client=client,
            customer_account=fields.customer_account,
            organization_name=fields.organization_name,
            customer_group_id=fields.customer_group_id,
        )
    except (SystemExit, Exception) as exc:
        logger.error("D365 customer creation failed: %s", exc)
        return _make_twiml_reply(
            "Failed to create customer in D365 F&O. "
            "Please try again later or contact an administrator."
        )

    # Step 7: Send confirmation
    account = created.get("CustomerAccount", fields.customer_account)
    name = created.get("OrganizationName", fields.organization_name)
    group = created.get("CustomerGroupId", fields.customer_group_id)

    confirmation = (
        "Customer created successfully in D365 F&O!\n\n"
        f"Account: {account}\n"
        f"Name: {name}\n"
        f"Group: {group}"
    )
    logger.info("Customer created: %s / %s / %s", account, name, group)
    return _make_twiml_reply(confirmation)


def _build_original_url(req: request) -> str:
    """Reconstruct the original public URL when behind a reverse proxy (e.g. ngrok).

    Ngrok forwards X-Forwarded-Proto and X-Forwarded-Host headers.
    Twilio signs requests using the public URL, so we must validate
    against that URL — not the local Flask URL.
    """
    forwarded_proto = req.headers.get("X-Forwarded-Proto")
    forwarded_host = req.headers.get("X-Forwarded-Host") or req.headers.get("Host")

    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}{req.path}"
    return req.url


def _validate_twilio_request(validator: RequestValidator, req: request) -> bool:
    """Validate that an incoming request genuinely came from Twilio.

    Uses forwarded headers to reconstruct the public URL when behind
    a reverse proxy like ngrok, since Twilio signs using the public URL.
    """
    signature = req.headers.get("X-Twilio-Signature", "")
    url = _build_original_url(req)
    logger.debug("Validating Twilio signature against URL: %s", url)
    return validator.validate(url, req.form.to_dict(), signature)


def _download_audio(
    media_url: str, twilio_account_sid: str, twilio_auth_token: str
) -> bytes:
    """Download audio file from Twilio media URL.

    Args:
        media_url: The MediaUrl0 value from the Twilio webhook payload.
        twilio_account_sid: Twilio account SID for authentication.
        twilio_auth_token: Twilio auth token for authentication.

    Returns:
        Raw audio file bytes.

    Raises:
        RuntimeError: If the download fails.
    """
    logger.info("Downloading audio from Twilio: %s", media_url)
    resp = http_requests.get(
        media_url,
        auth=(twilio_account_sid, twilio_auth_token),
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Audio download failed with status {resp.status_code}"
        )
    logger.info("Audio downloaded: %d bytes", len(resp.content))
    return resp.content


def _get_d365_client(config: WhatsAppConfig) -> D365ApiClient:
    """Authenticate to D365 and return an API client.

    Re-authenticates on each call to ensure token freshness.
    """
    authenticator = D365Authenticator(
        tenant_id=config.d365_tenant_id,
        client_id=config.d365_client_id,
        client_secret=config.d365_client_secret,
        environment_url=config.d365_environment_url,
    )
    token = authenticator.get_access_token()
    return D365ApiClient(
        environment_url=config.d365_environment_url,
        access_token=token,
    )


def _make_twiml_reply(message: str) -> Response:
    """Build a TwiML XML response with a text message body."""
    resp = MessagingResponse()
    resp.message(message)
    return Response(str(resp), content_type="text/xml")
