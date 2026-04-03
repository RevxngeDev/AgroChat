from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from src.query_normalizer import normalize_query_for_retrieval
from src.retriever import retrieve
from src.prompt_builder import build_prompt
from src.llm_client import get_completion
from src.response_builder import build_response
from src.languages import get_lang_pack

logger = logging.getLogger(__name__)


@dataclass
class QueryServiceResult:
    answer: str
    sources: list[dict[str, Any]]
    model: str
    lang: str
    elapsed_sec: float
    chunks_found: int
    retrieval_query: str


def _is_retryable_error(error: Exception) -> bool:
    msg = str(error).lower()
    retry_signals = [
        "429",
        "rate limit",
        "rate_limit",
        "timed out",
        "timeout",
        "request timed out",
        "connection error",
        "temporarily unavailable",
        "handshake operation timed out",
    ]
    return any(signal in msg for signal in retry_signals)


def _get_completion_with_retry(
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_retries: int = 3,
) -> str:
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return get_completion(system_prompt, user_prompt, model=model)
        except Exception as e:
            last_error = e

            if not _is_retryable_error(e) or attempt == max_retries:
                raise

            wait_seconds = min(2 * attempt, 8)
            logger.warning(
                "Temporary LLM error (attempt %d/%d): %s. Retrying in %.1fs",
                attempt,
                max_retries,
                e,
                wait_seconds,
            )
            time.sleep(wait_seconds)

    raise last_error


def run_query(
    *,
    index: Any,
    question: str,
    lang: str,
    model: str,
    top_k: int,
) -> QueryServiceResult:
    """
    Reusable AgroChat query pipeline for CLI/API.

    Retrieval is performed with a normalized Spanish query when needed,
    but the final response remains in the user's selected language.
    """
    start = time.time()

    retrieval_query = normalize_query_for_retrieval(question, lang)
    chunks = retrieve(index, retrieval_query, top_k=top_k)

    if not chunks:
        elapsed = time.time() - start
        return QueryServiceResult(
            answer=get_lang_pack(lang)["no_relevant_chunks"],
            sources=[],
            model=model,
            lang=lang,
            elapsed_sec=round(elapsed, 2),
            chunks_found=0,
            retrieval_query=retrieval_query,
        )

    system_prompt, user_prompt = build_prompt(question, chunks, lang=lang)
    answer = _get_completion_with_retry(
        system_prompt,
        user_prompt,
        model=model,
        max_retries=3,
    )

    rag_resp = build_response(answer, chunks, question, model, lang)

    elapsed = time.time() - start
    return QueryServiceResult(
        answer=rag_resp.answer,
        sources=rag_resp.sources,
        model=rag_resp.model,
        lang=rag_resp.lang,
        elapsed_sec=round(elapsed, 2),
        chunks_found=len(chunks),
        retrieval_query=retrieval_query,
    )