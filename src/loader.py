"""
AgroChat MVP — Document loader.
Loads PDFs from data/docs/<crop>/ and attaches crop metadata to each document.
"""

import logging
from pathlib import Path

from llama_index.core import Document
from llama_index.readers.file import PDFReader

from src import config

logger = logging.getLogger(__name__)


def load_documents() -> list[Document]:
    """
    Scan DOCS_DIR for PDFs organized in crop subfolders.
    Each document gets metadata: crop, source_file, subfolder.

    Returns:
        List of LlamaIndex Document objects with enriched metadata.
    """
    reader = PDFReader()
    all_docs: list[Document] = []

    for folder_name, crop_label in config.CROP_FOLDERS.items():
        folder_path: Path = config.DOCS_DIR / folder_name
        if not folder_path.exists():
            logger.warning("Crop folder not found: %s", folder_path)
            continue

        pdf_files = sorted(folder_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDFs in %s", folder_path)
            continue

        logger.info("Loading %d PDF(s) from '%s' (crop: %s)", len(pdf_files), folder_name, crop_label)

        for pdf_path in pdf_files:
            try:
                docs = reader.load_data(file=pdf_path)
                for doc in docs:
                    doc.metadata.update({
                        "crop": crop_label,
                        "source_file": pdf_path.name,
                        "subfolder": folder_name,
                    })
                all_docs.extend(docs)
                logger.info("  Loaded %s (%d pages)", pdf_path.name, len(docs))
            except Exception:
                logger.exception("Failed to load %s", pdf_path.name)

    logger.info("Total documents loaded: %d", len(all_docs))
    return all_docs
