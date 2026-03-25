"""
AgroChat MVP — Response builder.
Formats the LLM answer together with source citations and relevance scores
into a structured output for display.
"""

from dataclasses import dataclass

from src.retriever import RetrievedChunk


@dataclass
class RAGResponse:
    """Structured response from the RAG pipeline."""
    answer: str
    sources: list[dict]
    query: str
    model: str
    lang: str


def build_response(
    answer: str,
    chunks: list[RetrievedChunk],
    query: str,
    model: str,
    lang: str,
) -> RAGResponse:
    """
    Combine the LLM answer with source metadata into a structured response.

    Args:
        answer: Raw text from the LLM.
        chunks: Retrieved chunks used as context.
        query: Original user query.
        model: LLM model name used.
        lang: Language code.

    Returns:
        RAGResponse with answer and deduplicated sources.
    """
    # Deduplicate sources by file name
    seen_files: set[str] = set()
    sources: list[dict] = []
    for chunk in chunks:
        if chunk.source_file not in seen_files:
            seen_files.add(chunk.source_file)
            sources.append({
                "file": chunk.source_file,
                "crop": chunk.crop,
                "page": chunk.page_label,
                "score": chunk.score,
            })

    return RAGResponse(
        answer=answer,
        sources=sources,
        query=query,
        model=model,
        lang=lang,
    )
