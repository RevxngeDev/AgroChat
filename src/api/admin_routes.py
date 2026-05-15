"""
AgroChat — Admin API routes.
Endpoints for the admin dashboard: stats, logs, feedback, documents.
"""

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, File, Form, UploadFile

from src import config
from src.db.supabase_client import (
    get_all_crops,
    get_documents_with_crops,
    get_feedback_list,
    get_feedback_stats,
    get_query_logs,
    get_query_logs_count,
    get_users_count,
    get_crop_by_name,
    get_unindexed_documents,
    register_document,
    upload_pdf,
    download_pdf,
    mark_document_indexed,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


def _check_admin_key(x_api_key: str | None) -> None:
    if not config.ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not configured")
    if x_api_key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/dashboard")
def get_dashboard(x_api_key: str | None = Header(default=None)) -> dict:
    _check_admin_key(x_api_key)

    feedback = get_feedback_stats()
    total_logs = get_query_logs_count()
    total_users = get_users_count()
    documents = get_documents_with_crops()
    crops = get_all_crops()

    total_docs = len(documents)
    indexed_docs = sum(1 for d in documents if d.get("is_indexed"))

    return {
        "total_queries": total_logs,
        "total_users": total_users,
        "total_documents": total_docs,
        "indexed_documents": indexed_docs,
        "total_crops": len(crops),
        "feedback": feedback,
    }


@router.get("/query-logs")
def list_query_logs(
    limit: int = 50,
    offset: int = 0,
    x_api_key: str | None = Header(default=None),
) -> dict:
    _check_admin_key(x_api_key)

    logs = get_query_logs(limit=limit, offset=offset)
    total = get_query_logs_count()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": logs,
    }


@router.get("/feedback")
def list_feedback(
    limit: int = 50,
    x_api_key: str | None = Header(default=None),
) -> dict:
    _check_admin_key(x_api_key)

    stats = get_feedback_stats()
    entries = get_feedback_list(limit=limit)

    return {
        "stats": stats,
        "data": entries,
    }


@router.get("/documents")
def list_documents(x_api_key: str | None = Header(default=None)) -> dict:
    _check_admin_key(x_api_key)

    documents = get_documents_with_crops()
    crops = get_all_crops()

    return {
        "crops": crops,
        "documents": documents,
    }


@router.post("/documents/upload")
async def upload_document(
    crop: str = Form(..., description="Crop folder name, e.g. coffee or cocoa"),
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
) -> dict:
    _check_admin_key(x_api_key)

    crop_record = get_crop_by_name(crop)
    if not crop_record:
        raise HTTPException(
            status_code=400,
            detail=f"Crop '{crop}' not found. Available: {[c['name'] for c in get_all_crops()]}",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty.")

        storage_path = f"{crop}/{file.filename}"
        upload_pdf(storage_path, content)

        doc = register_document(
            crop_id=crop_record["id"],
            file_name=file.filename,
            storage_path=storage_path,
        )

        return {
            "ok": True,
            "message": "Document uploaded. Run reindex to add it to the search index.",
            "document": doc,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    finally:
        await file.close()
        
@router.post("/reindex")
def trigger_reindex(x_api_key: str | None = Header(default=None)) -> dict:
    _check_admin_key(x_api_key)

    import tempfile
    from pathlib import Path
    from llama_index.core import Document
    from llama_index.readers.file import PDFReader
    from src.core.indexer import add_to_index

    unindexed = get_unindexed_documents()
    if not unindexed:
        return {
            "ok": True,
            "message": "All documents are already indexed.",
            "documents_indexed": 0,
            "pages_added": 0,
        }

    reader = PDFReader()
    all_docs: list[Document] = []
    processed_ids: list[int] = []

    for doc_record in unindexed:
        file_name = doc_record["file_name"]
        storage_path = doc_record["storage_path"]
        crop_label = doc_record["crops"]["label"] if doc_record.get("crops") else "unknown"
        crop_name = doc_record["crops"]["name"] if doc_record.get("crops") else "unknown"

        try:
            pdf_bytes = download_pdf(storage_path)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = Path(tmp.name)

            pages = reader.load_data(file=tmp_path)
            for page in pages:
                page.metadata.update({
                    "crop": crop_label,
                    "source_file": file_name,
                    "subfolder": crop_name,
                })
            all_docs.extend(pages)
            processed_ids.append(doc_record["id"])

            tmp_path.unlink(missing_ok=True)
            logger.info("Processed: %s (%d pages)", file_name, len(pages))

        except Exception as e:
            logger.exception("Failed to process %s: %s", file_name, e)

    if not all_docs:
        raise HTTPException(status_code=500, detail="No documents were processed successfully.")

    add_to_index(all_docs)

    for doc_id in processed_ids:
        mark_document_indexed(doc_id)

    # Reload index in main app
    from src.api.main import reload_index
    reload_index()

    return {
        "ok": True,
        "message": f"Indexed {len(processed_ids)} document(s), {len(all_docs)} pages.",
        "documents_indexed": len(processed_ids),
        "pages_added": len(all_docs),
    }