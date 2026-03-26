from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from src import config
from src.indexer import load_index
from src.api.schemas import (
    ConfigResponse,
    HealthResponse,
    IndexStatusResponse,
    QueryRequest,
    QueryResponse,
)
from src.services.query_service import run_query

app = FastAPI(
    title="AgroChat API",
    version="0.1.0",
    description="API del chatbot agrícola inteligente AgroChat",
)

logger = logging.getLogger(__name__)

_INDEX = None


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