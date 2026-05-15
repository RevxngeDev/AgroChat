"""
AgroChat MVP — Central configuration.
Loads settings from .env and exposes them as module-level constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# --- Paths ---
DOCS_DIR: Path = _PROJECT_ROOT / os.getenv("DOCS_DIR", "data/docs")
INDEX_DIR: Path = _PROJECT_ROOT / os.getenv("INDEX_DIR", "data/index")
LOG_DIR: Path = _PROJECT_ROOT / os.getenv("LOG_DIR", "logs")
TEMP_AUDIO_DIR: Path = _PROJECT_ROOT / os.getenv("TEMP_AUDIO_DIR", "temp/audio")

# --- Supabase ---
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
# --- Admin ---
ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")

# --- LLM ---
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE_URL: str = os.getenv("AGROCHAT_API_BASE_URL", "http://127.0.0.1:8000")
GROQ_STT_MODEL: str = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
EDGE_TTS_VOICE_ES: str = os.getenv("EDGE_TTS_VOICE_ES", "es-CO-SalomeNeural")
EDGE_TTS_VOICE_EN: str = os.getenv("EDGE_TTS_VOICE_EN", "en-US-AriaNeural")
EDGE_TTS_VOICE_RU: str = os.getenv("EDGE_TTS_VOICE_RU", "ru-RU-SvetlanaNeural")
TEMP_TTS_DIR: Path = _PROJECT_ROOT / os.getenv("TEMP_TTS_DIR", "temp/tts")

# --- Embeddings ---
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EMBEDDING_DIM: int = 384  # MiniLM-L12-v2 output dimensions

# --- RAG parameters ---
TOP_K: int = int(os.getenv("TOP_K", "5"))
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "64"))

# --- Language ---
DEFAULT_LANG: str = os.getenv("DEFAULT_LANG", "es")

# --- Crop metadata mapping ---
# Maps subfolder names under DOCS_DIR to crop labels used in metadata.
# Fallback crops (used if Supabase is not available)
_DEFAULT_CROP_FOLDERS: dict[str, str] = {
    "avocado": "aguacate",
    "banana": "banano",
    "cocoa": "cacao",
    "coffee": "café",
    "corn": "maíz",
    "rice": "arroz",
}


def get_crop_folders() -> dict[str, str]:
    """Load crops from Supabase. Falls back to hardcoded if unavailable."""
    try:
        from src.db.supabase_client import get_crop_folders as _db_crops
        crops = _db_crops()
        if crops:
            return crops
    except Exception:
        pass
    return _DEFAULT_CROP_FOLDERS


# For backward compatibility
CROP_FOLDERS: dict[str, str] = _DEFAULT_CROP_FOLDERS

def validate() -> list[str]:
    """Return a list of configuration warnings (empty = all good)."""
    warnings: list[str] = []
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        warnings.append("GROQ_API_KEY is not set. Copy .env.example → .env and add your key.")
    if not SUPABASE_URL or SUPABASE_URL == "your_supabase_url_here":
        warnings.append("SUPABASE_URL is not set. Check your .env file.")
    if not SUPABASE_KEY or SUPABASE_KEY == "your_supabase_anon_key_here":
        warnings.append("SUPABASE_KEY is not set. Check your .env file.")
    if not DOCS_DIR.exists():
        warnings.append(f"DOCS_DIR does not exist: {DOCS_DIR}")
    return warnings
