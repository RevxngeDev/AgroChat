"""
AgroChat MVP — Text to Speech.
Generates speech audio files from text using edge-tts.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import edge_tts

from src import config

logger = logging.getLogger(__name__)


def get_tts_voice_for_lang(lang: str) -> str:
    """Return configured TTS voice for language."""
    if lang == "en":
        return config.EDGE_TTS_VOICE_EN
    if lang == "ru":
        return config.EDGE_TTS_VOICE_RU
    return config.EDGE_TTS_VOICE_ES


async def synthesize_speech_to_file_async(
    text: str,
    output_path: str | Path,
    lang: str,
) -> Path:
    """
    Generate speech audio from text and save it to a local file.

    Args:
        text: Text to synthesize.
        output_path: Destination audio file path.
        lang: Language code for selecting voice.

    Returns:
        Path to generated audio file.
    """
    if not text.strip():
        raise ValueError("Text for speech synthesis is empty.")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    voice = get_tts_voice_for_lang(lang)

    logger.info("Generating TTS audio with edge-tts: %s | voice=%s", out_path.name, voice)

    communicator = edge_tts.Communicate(text=text, voice=voice)
    await communicator.save(str(out_path))

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("TTS output file was not generated correctly.")

    logger.info("TTS audio generated successfully (%d bytes)", out_path.stat().st_size)
    return out_path


def synthesize_speech_to_file(
    text: str,
    output_path: str | Path,
    lang: str,
) -> Path:
    """
    Sync wrapper for edge-tts generation.
    """
    return asyncio.run(synthesize_speech_to_file_async(text, output_path, lang))