from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, UploadFile

from src import config
from src.indexer import build_index, load_index
from src.loader import load_documents
from src.api.schemas import (
    BasicMetricsResponse,
    ConfigResponse,
    CropMetricItem,
    DocumentItem,
    HealthResponse,
    IndexStatusResponse,
    QueryRequest,
    QueryResponse,
    ReindexResponse,
    UploadDocumentResponse,
)
from src.services.query_service import run_query

app = FastAPI(
    title="AgroChat API",
    version="0.1.0",
    description="API del chatbot agrícola inteligente AgroChat",
)

logger = logging.getLogger(__name__)

_INDEX = None


def _check_admin_key(x_api_key: str | None) -> None:
    if not config.ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY no está configurada en .env")

    if x_api_key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")


@app.on_event("startup")
def startup_event() -> None:
    global _INDEX
    try:
        _INDEX = load_index()
        logger.info("AgroChat index loaded successfully on startup.")
    except Exception as e:
        logger.exception("Failed to load index on startup: %s", e)
        _INDEX = None


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        name="AgroChat API",
        index_loaded=_INDEX is not None,
    )


@app.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return ConfigResponse(
        name="AgroChat API",
        default_lang=config.DEFAULT_LANG,
        default_model=config.LLM_MODEL,
        default_top_k=config.TOP_K,
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        embedding_model=config.EMBEDDING_MODEL,
        crops=list(config.CROP_FOLDERS.values()),
    )


@app.get("/status/index", response_model=IndexStatusResponse)
def get_index_status() -> IndexStatusResponse:
    return IndexStatusResponse(
        index_loaded=_INDEX is not None,
        index_dir=str(config.INDEX_DIR),
        docs_dir=str(config.DOCS_DIR),
        log_dir=str(config.LOG_DIR),
        index_exists=config.INDEX_DIR.exists(),
    )


@app.get("/admin/documents", response_model=list[DocumentItem])
def list_documents(
    crop: str | None = Query(default=None, description="Filtrar por carpeta de cultivo, ej. coffee o cocoa"),
    x_api_key: str | None = Header(default=None),
) -> list[DocumentItem]:
    _check_admin_key(x_api_key)

    items: list[DocumentItem] = []

    for folder_name, crop_label in config.CROP_FOLDERS.items():
        if crop and folder_name != crop:
            continue

        folder_path: Path = config.DOCS_DIR / folder_name
        if not folder_path.exists():
            continue

        pdf_files = sorted(folder_path.glob("*.pdf"))
        for pdf_path in pdf_files:
            items.append(
                DocumentItem(
                    file_name=pdf_path.name,
                    crop_folder=folder_name,
                    crop_label=crop_label,
                    relative_path=str(pdf_path.relative_to(config.DOCS_DIR.parent)),
                    size_bytes=pdf_path.stat().st_size,
                )
            )

    return items


@app.get("/admin/metrics/basic", response_model=BasicMetricsResponse)
def get_basic_metrics(x_api_key: str | None = Header(default=None)) -> BasicMetricsResponse:
    _check_admin_key(x_api_key)

    crop_metrics: list[CropMetricItem] = []
    total_pdfs = 0

    for folder_name, crop_label in config.CROP_FOLDERS.items():
        folder_path = config.DOCS_DIR / folder_name
        pdf_count = 0

        if folder_path.exists():
            pdf_count = len(list(folder_path.glob("*.pdf")))

        total_pdfs += pdf_count
        crop_metrics.append(
            CropMetricItem(
                crop_folder=folder_name,
                crop_label=crop_label,
                pdf_count=pdf_count,
            )
        )

    return BasicMetricsResponse(
        name="AgroChat API",
        index_loaded=_INDEX is not None,
        index_exists=config.INDEX_DIR.exists(),
        total_crops=len(config.CROP_FOLDERS),
        total_pdfs=total_pdfs,
        crops=crop_metrics,
    )


@app.post("/admin/documents/upload", response_model=UploadDocumentResponse)
async def upload_document(
    crop: str = Form(..., description="Carpeta de cultivo destino, ej. coffee o cocoa"),
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
) -> UploadDocumentResponse:
    _check_admin_key(x_api_key)

    if crop not in config.CROP_FOLDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Crop inválido. Valores permitidos: {list(config.CROP_FOLDERS.keys())}"
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo no tiene nombre.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF.")

    target_dir = config.DOCS_DIR / crop
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / file.filename
    if target_path.exists():
        raise HTTPException(status_code=409, detail="Ya existe un archivo con ese nombre en ese cultivo.")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")

        target_path.write_bytes(content)

        return UploadDocumentResponse(
            ok=True,
            message="Documento subido correctamente. Recuerda ejecutar /admin/reindex para incorporarlo al índice.",
            file_name=target_path.name,
            crop_folder=crop,
            crop_label=config.CROP_FOLDERS[crop],
            relative_path=str(target_path.relative_to(config.DOCS_DIR.parent)),
            size_bytes=target_path.stat().st_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al subir el documento: {e}")
    finally:
        await file.close()


@app.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest) -> QueryResponse:
    global _INDEX

    if _INDEX is None:
        try:
            _INDEX = load_index()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Index is not available: {e}")

    model_name = payload.model or config.LLM_MODEL
    top_k = payload.top_k or config.TOP_K

    try:
        result = run_query(
            index=_INDEX,
            question=payload.question,
            lang=payload.lang,
            model=model_name,
            top_k=top_k,
        )
        return QueryResponse(
            answer=result.answer,
            sources=result.sources,
            model=result.model,
            lang=result.lang,
            elapsed_sec=result.elapsed_sec,
            chunks_found=result.chunks_found,
        )
    except Exception as e:
        logger.exception("Query failed: %s", e)

        msg = str(e).lower()
        if "timed out" in msg or "timeout" in msg:
            raise HTTPException(
                status_code=504,
                detail="La consulta al modelo tardó demasiado. Intenta de nuevo en unos segundos."
            )

        if "429" in msg or "rate limit" in msg:
            raise HTTPException(
                status_code=429,
                detail="Se alcanzó temporalmente el límite de uso del modelo. Intenta nuevamente en un momento."
            )

        raise HTTPException(status_code=500, detail=f"Error interno al procesar la consulta: {e}")


@app.post("/admin/reindex", response_model=ReindexResponse)
def admin_reindex(x_api_key: str | None = Header(default=None)) -> ReindexResponse:
    global _INDEX
    _check_admin_key(x_api_key)

    try:
        docs = load_documents()
        if not docs:
            raise HTTPException(status_code=400, detail="No se encontraron documentos para indexar")

        build_index(docs)
        _INDEX = load_index()

        return ReindexResponse(
            ok=True,
            message="Índice reconstruido y recargado correctamente.",
            docs_loaded=len(docs),
            index_dir=str(config.INDEX_DIR),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reindex failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al reconstruir el índice: {e}")