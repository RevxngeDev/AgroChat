"""
AgroChat MVP — Supabase client.
Centralizes all communication with Supabase (database + storage).
"""

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import create_client, Client

from src import config

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    """Get or create the Supabase client singleton."""
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


# ── Crops ──

def get_all_crops() -> list[dict]:
    """Fetch all crops from the database."""
    response = get_client().table("crops").select("*").execute()
    return response.data


def get_crop_by_name(name: str) -> dict | None:
    """Fetch a single crop by its folder name."""
    response = get_client().table("crops").select("*").eq("name", name).execute()
    return response.data[0] if response.data else None


# ── Documents ──

def get_all_documents() -> list[dict]:
    """Fetch all document records."""
    response = get_client().table("documents").select("*, crops(name, label)").execute()
    return response.data


def get_unindexed_documents() -> list[dict]:
    """Fetch documents that have not been indexed yet."""
    response = (
        get_client()
        .table("documents")
        .select("*, crops(name, label)")
        .eq("is_indexed", False)
        .execute()
    )
    return response.data


def register_document(crop_id: int, file_name: str, storage_path: str, page_count: int | None = None) -> dict:
    """Register a new document in the database."""
    response = (
        get_client()
        .table("documents")
        .insert({
            "crop_id": crop_id,
            "file_name": file_name,
            "storage_path": storage_path,
            "page_count": page_count,
        })
        .execute()
    )
    logger.info("Registered document: %s", file_name)
    return response.data[0]


def mark_document_indexed(doc_id: int) -> None:
    """Mark a document as indexed."""
    (
        get_client()
        .table("documents")
        .update({
            "is_indexed": True,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", doc_id)
        .execute()
    )
    logger.info("Marked document %d as indexed", doc_id)


# ── Storage ──

def upload_pdf(storage_path: str, file_bytes: bytes, max_retries: int = 3) -> str:
    """
    Upload a PDF to Supabase Storage with retry logic.

    Args:
        storage_path: Path within the bucket (e.g., 'coffee/doc1.pdf')
        file_bytes: Raw PDF content.
        max_retries: Number of retry attempts.

    Returns:
        The storage path used.
    """
    import time

    for attempt in range(1, max_retries + 1):
        try:
            get_client().storage.from_("documents").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": "application/pdf"},
            )
            logger.info("Uploaded PDF to storage: %s", storage_path)
            return storage_path
        except Exception as e:
            if attempt == max_retries:
                raise
            wait = min(5 * attempt, 15)
            logger.warning(
                "Upload failed (attempt %d/%d): %s. Retrying in %ds...",
                attempt, max_retries, e, wait,
            )
            time.sleep(wait)

    return storage_path


def download_pdf(storage_path: str) -> bytes:
    """Download a PDF from Supabase Storage."""
    response = get_client().storage.from_("documents").download(storage_path)
    logger.info("Downloaded PDF from storage: %s", storage_path)
    return response


# ── Users ──

def get_or_create_user(telegram_id: int) -> dict:
    """Get existing user or create a new one."""
    response = (
        get_client()
        .table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    if response.data:
        return response.data[0]

    response = (
        get_client()
        .table("users")
        .insert({"telegram_id": telegram_id})
        .execute()
    )
    logger.info("Created new user: telegram_id=%d", telegram_id)
    return response.data[0]


def update_user_lang(telegram_id: int, lang: str) -> None:
    """Update user's language preference."""
    (
        get_client()
        .table("users")
        .update({
            "lang": lang,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("telegram_id", telegram_id)
        .execute()
    )


def update_user_voice(telegram_id: int, voice_enabled: bool) -> None:
    """Update user's voice preference."""
    (
        get_client()
        .table("users")
        .update({
            "voice_enabled": voice_enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("telegram_id", telegram_id)
        .execute()
    )


# ── Query logs ──

def log_query(
    user_id: int | None,
    question: str,
    retrieval_query: str | None,
    answer: str,
    sources: list[dict],
    model: str,
    lang: str,
    elapsed_sec: float,
    chunks_found: int,
) -> dict:
    """Log a query and its response to the database."""
    import json

    response = (
        get_client()
        .table("query_logs")
        .insert({
            "user_id": user_id,
            "question": question,
            "retrieval_query": retrieval_query,
            "answer": answer,
            "sources": json.dumps(sources),
            "model": model,
            "lang": lang,
            "elapsed_sec": elapsed_sec,
            "chunks_found": chunks_found,
        })
        .execute()
    )
    logger.info("Logged query: '%s'", question[:50])
    return response.data[0]


# ── Feedback ──

def save_feedback(query_log_id: int, rating: int, comment: str | None = None) -> dict:
    """Save user feedback for a query."""
    response = (
        get_client()
        .table("feedback")
        .insert({
            "query_log_id": query_log_id,
            "rating": rating,
            "comment": comment,
        })
        .execute()
    )
    logger.info("Saved feedback for query_log %d: rating=%d", query_log_id, rating)
    return response.data[0]