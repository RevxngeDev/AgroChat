"""
AgroChat MVP — Speech to Text.
Transcribes audio files using Groq Speech-to-Text.
"""

from __future__ import annotations

import logging
from pathlib import Path

from groq import Groq

from src import config

logger = logging.getLogger(__name__)


def transcribe_audio_file(file_path: str | Path) -> str:
    """
    Transcribe an audio file to text using Groq STT.

    Args:
        file_path: Path to local audio file.

    Returns:
        Transcribed text.

    Raises:
        ValueError: If GROQ_API_KEY is not configured.
        RuntimeError: If transcription fails or returns empty text.
    """
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Check your .env file.")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    client = Groq(api_key=config.GROQ_API_KEY)

    logger.info("Transcribing audio with Groq STT: %s", path.name)

    with path.open("rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=config.GROQ_STT_MODEL,
            response_format="json",
            temperature=0.0,
        )

    text = ""

    # Compatible handling depending on SDK response shape
    if hasattr(transcription, "text"):
        text = transcription.text or ""
    elif isinstance(transcription, dict):
        text = transcription.get("text", "") or ""

    text = text.strip()

    if not text:
        raise RuntimeError("Empty transcription result from Groq STT.")

    logger.info("Audio transcribed successfully (%d chars)", len(text))
    return text