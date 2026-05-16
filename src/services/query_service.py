from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from src.core.query_normalizer import normalize_query_for_retrieval
from src.core.retriever import retrieve
from src.core.prompt_builder import build_prompt
from src.core.llm_client import get_completion
from src.core.response_builder import build_response
from src.languages import get_lang_pack
from src.db.supabase_client import log_query
from src.core.crop_detector import detect_crops

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
    query_log_id: int | None = None


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
    user_id: int | None = None,
    conversation_history: str = "",
) -> QueryServiceResult:
    """
    Reusable AgroChat query pipeline for CLI/API.

    Retrieval is performed with a normalized Spanish query when needed,
    but the final response remains in the user's selected language.
    """
    start = time.time()

    retrieval_query = normalize_query_for_retrieval(question, lang)
    detected_crops = detect_crops(question)
    chunks = retrieve(index, retrieval_query, top_k=top_k, crop_filter=detected_crops or None)

    if not chunks:
        elapsed = time.time() - start
        empty_answer = get_lang_pack(lang)["no_relevant_chunks"]

        log_id = None
        try:
            log_record = log_query(
                user_id=user_id,
                question=question,
                retrieval_query=retrieval_query,
                answer=empty_answer,
                sources=[],
                model=model,
                lang=lang,
                elapsed_sec=round(elapsed, 2),
                chunks_found=0,
            )
            log_id = log_record.get("id")
        except Exception as e:
            logger.warning("Failed to log query: %s", e)

        return QueryServiceResult(
            answer=empty_answer,
            sources=[],
            model=model,
            lang=lang,
            elapsed_sec=round(elapsed, 2),
            chunks_found=0,
            retrieval_query=retrieval_query,
            query_log_id=log_id,
        )

    system_prompt, user_prompt = build_prompt(question, chunks, lang=lang, conversation_history=conversation_history)
    answer = _get_completion_with_retry(
        system_prompt,
        user_prompt,
        model=model,
        max_retries=3,
    )

    rag_resp = build_response(answer, chunks, question, model, lang)
    elapsed = time.time() - start

    log_id = None
    try:
        log_record = log_query(
            user_id=user_id,
            question=question,
            retrieval_query=retrieval_query,
            answer=rag_resp.answer,
            sources=rag_resp.sources,
            model=model,
            lang=lang,
            elapsed_sec=round(elapsed, 2),
            chunks_found=len(chunks),
        )
        log_id = log_record.get("id")
    except Exception as e:
        logger.warning("Failed to log query: %s", e)

    return QueryServiceResult(
        answer=rag_resp.answer,
        sources=rag_resp.sources,
        model=rag_resp.model,
        lang=rag_resp.lang,
        elapsed_sec=round(elapsed, 2),
        chunks_found=len(chunks),
        retrieval_query=retrieval_query,
        query_log_id=log_id,
    )