"""Speech-to-text transcription via OpenAI Whisper API."""

import io
import logging

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""


def transcribe_audio(
    audio_data: bytes, api_key: str, filename: str = "voice.ogg"
) -> str:
    """Transcribe audio bytes using OpenAI Whisper API.

    Args:
        audio_data: Raw audio file bytes (ogg/opus from Twilio).
        api_key: OpenAI API key.
        filename: Name hint for the audio file (format detection).

    Returns:
        Transcribed text string.

    Raises:
        TranscriptionError: If the Whisper API call fails or returns empty text.
    """
    client = OpenAI(api_key=api_key)
    audio_file = io.BytesIO(audio_data)
    audio_file.name = filename

    try:
        logger.info("Sending audio to OpenAI Whisper for transcription...")
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
    except (APIError, APIConnectionError, RateLimitError) as exc:
        logger.error("Whisper API error: %s", exc)
        raise TranscriptionError(f"Whisper transcription failed: {exc}") from exc

    text = result.text.strip()
    if not text:
        logger.warning("Whisper returned empty transcription.")
        raise TranscriptionError("Transcription returned empty text.")

    logger.info("Transcription result: %s", text)
    return text
