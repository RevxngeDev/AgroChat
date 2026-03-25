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

# --- LLM ---
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

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
CROP_FOLDERS: dict[str, str] = {
    "coffee": "café",
    "cocoa": "cacao",
}


def validate() -> list[str]:
    """Return a list of configuration warnings (empty = all good)."""
    warnings: list[str] = []
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        warnings.append("GROQ_API_KEY is not set. Copy .env.example → .env and add your key.")
    if not DOCS_DIR.exists():
        warnings.append(f"DOCS_DIR does not exist: {DOCS_DIR}")
    return warnings
