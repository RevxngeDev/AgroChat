"""
AgroChat MVP — Retriever.
Performs similarity search against the FAISS index and returns
ranked chunks with metadata.

For comparative queries that mention multiple configured crops,
it uses a balanced retrieval strategy to improve evidence coverage.
"""

import logging
import re
import unicodedata
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


def _normalize_text(text: str) -> str:
    """
    Normalize text for simple rule-based matching:
    - lowercase
    - remove accents
    - collapse spaces
    """
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text


def _is_comparative_query(query: str) -> bool:
    """Heuristic detection of comparison-style questions."""
    q = _normalize_text(query)

    comparative_signals = [
        "diferencia",
        "diferencias",
        "semejanza",
        "semejanzas",
        "compar",
        "versus",
        " vs ",
        "ambos",
        "entre",
    ]

    return any(signal in q for signal in comparative_signals)


def _build_crop_aliases() -> dict[str, set[str]]:
    """
    Build aliases for crop detection from config.CROP_FOLDERS.

    Returns a mapping:
        canonical_label_in_metadata -> {aliases usable for query detection}

    Example with current config:
        {
            "café": {"cafe", "coffee", "café"},
            "cacao": {"cacao", "cocoa"},
        }
    """
    aliases: dict[str, set[str]] = {}

    for folder_name, crop_label in config.CROP_FOLDERS.items():
        canonical = crop_label.strip()
        normalized_folder = _normalize_text(folder_name)
        normalized_label = _normalize_text(crop_label)

        alias_set = {normalized_folder, normalized_label}

        # Optional hand-made aliases for common bilingual usage
        # This stays general enough and harmless if not used.
        extras = {
            "coffee": {"cafe", "coffee"},
            "cocoa": {"cacao", "cocoa"},
            "avocado": {"aguacate", "avocado"},
            "banana": {"banano", "banana"},
            "corn": {"maiz", "corn", "maize"},
            "rice": {"arroz", "rice"},
        }
        if normalized_folder in extras:
            alias_set.update(extras[normalized_folder])

        aliases[canonical] = alias_set

    return aliases


def _detect_mentioned_crops(query: str) -> list[str]:
    """
    Detect which configured crops are explicitly mentioned in the query.

    Returns the canonical crop labels as they appear in metadata,
    e.g. ["café", "cacao"].
    """
    q = f" {_normalize_text(query)} "
    crop_aliases = _build_crop_aliases()

    detected: list[str] = []
    for canonical_crop, aliases in crop_aliases.items():
        for alias in aliases:
            if f" {alias} " in q:
                detected.append(canonical_crop)
                break

    return detected


def _node_to_chunk(node: NodeWithScore) -> RetrievedChunk:
    """Convert a LlamaIndex NodeWithScore to RetrievedChunk."""
    meta = node.metadata or {}
    return RetrievedChunk(
        text=node.get_text(),
        score=round(node.score or 0.0, 4),
        crop=meta.get("crop", "unknown"),
        source_file=meta.get("source_file", "unknown"),
        page_label=meta.get("page_label", "?"),
    )


def _deduplicate_nodes(nodes: list[NodeWithScore]) -> list[NodeWithScore]:
    """
    Deduplicate nodes using a lightweight content/source signature.
    Keeps the first occurrence.
    """
    seen = set()
    unique_nodes = []

    for node in nodes:
        meta = node.metadata or {}
        key = (
            meta.get("source_file", "unknown"),
            meta.get("page_label", "?"),
            node.get_text()[:120],
        )
        if key not in seen:
            seen.add(key)
            unique_nodes.append(node)

    return unique_nodes


def _retrieve_standard(index: VectorStoreIndex, query: str, k: int) -> list[RetrievedChunk]:
    """Default retrieval behavior."""
    retriever = index.as_retriever(similarity_top_k=k)
    nodes: list[NodeWithScore] = retriever.retrieve(query)

    chunks = [_node_to_chunk(node) for node in nodes]
    logger.info("Standard retrieval returned %d chunks for query: '%s'", len(chunks), query[:80])
    return chunks


def _retrieve_balanced(index: VectorStoreIndex, query: str, k: int, target_crops: list[str]) -> list[RetrievedChunk]:
    """
    Balanced retrieval for comparative questions:
    - retrieve a wider candidate pool
    - keep results from the mentioned crops
    - try to include evidence from each mentioned crop
    - fill remaining slots with the most relevant leftovers
    """
    wide_k = max(k * 4, 12)
    retriever = index.as_retriever(similarity_top_k=wide_k)
    nodes: list[NodeWithScore] = retriever.retrieve(query)
    nodes = _deduplicate_nodes(nodes)

    target_set = {crop.strip().lower() for crop in target_crops}

    grouped: dict[str, list[NodeWithScore]] = {crop: [] for crop in target_set}
    other_nodes: list[NodeWithScore] = []

    for node in nodes:
        crop = ((node.metadata or {}).get("crop", "")).strip().lower()
        if crop in target_set:
            grouped[crop].append(node)
        else:
            other_nodes.append(node)

    selected: list[NodeWithScore] = []

    # 1) Guarantee one chunk per mentioned crop if available
    for crop in target_set:
        if grouped[crop]:
            selected.append(grouped[crop].pop(0))

    # 2) Round-robin among mentioned crops until reaching k
    while len(selected) < k:
        added_any = False
        for crop in target_set:
            if grouped[crop] and len(selected) < k:
                selected.append(grouped[crop].pop(0))
                added_any = True
        if not added_any:
            break

    # 3) Fill remaining slots with leftover relevant nodes
    remaining = []
    for crop in target_set:
        remaining.extend(grouped[crop])
    remaining.extend(other_nodes)

    for node in remaining:
        if len(selected) >= k:
            break
        selected.append(node)

    chunks = [_node_to_chunk(node) for node in selected]

    counts = {}
    for c in chunks:
        key = c.crop.lower()
        counts[key] = counts.get(key, 0) + 1

    logger.info(
        "Balanced retrieval returned %d chunks for query '%s' with crop counts=%s",
        len(chunks),
        query[:80],
        counts,
    )
    return chunks


def retrieve(index: VectorStoreIndex, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Strategy:
    - standard retrieval for normal questions
    - balanced retrieval for comparative questions mentioning 2+ configured crops
    """
    k = top_k or config.TOP_K

    mentioned_crops = _detect_mentioned_crops(query)
    is_comparative = _is_comparative_query(query)

    if is_comparative and len(mentioned_crops) >= 2:
        logger.info(
            "Comparative query detected. Mentioned crops: %s | query='%s'",
            mentioned_crops,
            query[:80],
        )
        chunks = _retrieve_balanced(index, query, k, mentioned_crops)
    else:
        chunks = _retrieve_standard(index, query, k)

    logger.info("Retrieved %d chunks for query: '%s'", len(chunks), query[:80])
    return chunks