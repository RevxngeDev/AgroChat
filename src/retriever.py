"""
AgroChat MVP — Retriever.
Performs similarity search against the FAISS index and returns
ranked chunks with metadata.
"""

import logging
from dataclasses import dataclass

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore

from src import config

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A single retrieved chunk with its metadata and relevance score."""
    text: str
    score: float
    crop: str
    source_file: str
    page_label: str  # page number from PDF metadata


def retrieve(index: VectorStoreIndex, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Args:
        index: The loaded VectorStoreIndex.
        query: User question in natural language.
        top_k: Number of results (defaults to config.TOP_K).

    Returns:
        List of RetrievedChunk sorted by relevance (best first).
    """
    k = top_k or config.TOP_K
    retriever = index.as_retriever(similarity_top_k=k)
    nodes: list[NodeWithScore] = retriever.retrieve(query)

    chunks: list[RetrievedChunk] = []
    for node in nodes:
        meta = node.metadata or {}
        chunks.append(RetrievedChunk(
            text=node.get_text(),
            score=round(node.score or 0.0, 4),
            crop=meta.get("crop", "unknown"),
            source_file=meta.get("source_file", "unknown"),
            page_label=meta.get("page_label", "?"),
        ))

    logger.info("Retrieved %d chunks for query: '%s'", len(chunks), query[:80])
    return chunks
