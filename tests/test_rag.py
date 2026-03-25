"""
AgroChat MVP — Test suite.
Basic evaluation questions for café and cacao RAG pipeline.
Run: pytest tests/test_rag.py -v
"""

import pytest
from src import config

# ── Evaluation questions (will be used in Phase 5) ──

EVAL_QUESTIONS_COFFEE = [
    "¿Cuáles son las principales plagas del café en Colombia?",
    "¿Qué variedades de café se recomiendan para zonas altas?",
    "¿Cómo se debe fertilizar un cafetal?",
    "¿Cuál es el manejo ambiental recomendado para café?",
    "¿A qué altitud se cultiva mejor el café en Colombia?",
]

EVAL_QUESTIONS_COCOA = [
    "¿Cuáles son las enfermedades más comunes del cacao?",
    "¿Cómo se debe podar un árbol de cacao?",
    "¿Qué suelos son ideales para el cultivo de cacao?",
    "¿Cuál es el proceso de fermentación del cacao?",
    "¿Qué variedades de cacao se cultivan en Colombia?",
]


class TestConfig:
    """Validate that the project configuration is correct."""

    def test_docs_dir_exists(self):
        assert config.DOCS_DIR.exists(), f"DOCS_DIR not found: {config.DOCS_DIR}"

    def test_crop_folders_exist(self):
        for folder_name in config.CROP_FOLDERS:
            path = config.DOCS_DIR / folder_name
            assert path.exists(), f"Crop folder not found: {path}"

    def test_embedding_dim(self):
        assert config.EMBEDDING_DIM == 384

    def test_groq_key_is_set(self):
        warnings = config.validate()
        api_warnings = [w for w in warnings if "GROQ_API_KEY" in w]
        assert not api_warnings, "GROQ_API_KEY is not configured"


class TestLoader:
    """Test document loading (requires PDFs in data/docs/)."""

    def test_load_documents_returns_list(self):
        from src.loader import load_documents
        docs = load_documents()
        assert isinstance(docs, list)
        assert len(docs) > 0, "No documents loaded — check data/docs/"

    def test_documents_have_crop_metadata(self):
        from src.loader import load_documents
        docs = load_documents()
        for doc in docs[:5]:
            assert "crop" in doc.metadata
            assert doc.metadata["crop"] in ("café", "cacao")
