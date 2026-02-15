"""Speech-to-text transcription via Azure Cognitive Services Speech API."""

import logging

import requests

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""


def transcribe_audio(audio_data: bytes, speech_key: str, speech_region: str) -> str:
    """Transcribe audio bytes using the Azure Speech-to-Text REST API.

    Args:
        audio_data: Raw audio file bytes (ogg/opus from Twilio).
        speech_key: Azure Speech Services subscription key.
        speech_region: Azure region (e.g., 'eastus', 'westeurope').

    Returns:
        Transcribed text string.

    Raises:
        TranscriptionError: If the API call fails or returns empty text.
    """
    url = (
        f"https://{speech_region}.stt.speech.microsoft.com"
        "/speech/recognition/conversation/cognitiveservices/v1"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": speech_key,
        "Content-Type": "audio/ogg; codecs=opus",
        "Accept": "application/json",
    }
    params = {"language": "en-US"}

    try:
        logger.info("Sending audio to Azure Speech Services for transcription...")
        resp = requests.post(
            url, headers=headers, params=params, data=audio_data, timeout=30
        )
    except requests.RequestException as exc:
        logger.error("Azure Speech API request failed: %s", exc)
        raise TranscriptionError(f"Speech transcription request failed: {exc}") from exc

    if resp.status_code != 200:
        logger.error("Azure Speech API returned %d: %s", resp.status_code, resp.text[:500])
        raise TranscriptionError(
            f"Speech API returned status {resp.status_code}"
        )

    data = resp.json()
    status = data.get("RecognitionStatus", "")

    if status != "Success":
        logger.warning("Azure Speech recognition status: %s", status)
        raise TranscriptionError(
            f"Speech recognition failed with status: {status}"
        )

    text = data.get("DisplayText", "").strip()
    if not text:
        logger.warning("Azure Speech returned empty transcription.")
        raise TranscriptionError("Transcription returned empty text.")

    logger.info("Transcription result: %s", text)
    return text
