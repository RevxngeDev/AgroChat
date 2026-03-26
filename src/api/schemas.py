from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pregunta del usuario")
    lang: str = Field(default="es", description="Idioma de respuesta")
    model: str | None = Field(default=None, description="Modelo LLM opcional")
    top_k: int | None = Field(default=None, ge=1, le=20, description="Número de chunks a recuperar")


class SourceItem(BaseModel):
    file: str
    crop: str
    page: str | int
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    model: str
    lang: str
    elapsed_sec: float
    chunks_found: int


class HealthResponse(BaseModel):
    ok: bool
    name: str
    index_loaded: bool


class ConfigResponse(BaseModel):
    name: str
    default_lang: str
    default_model: str
    default_top_k: int
    chunk_size: int
    chunk_overlap: int
    embedding_model: str
    crops: list[str]


class IndexStatusResponse(BaseModel):
    index_loaded: bool
    index_dir: str
    docs_dir: str
    log_dir: str
    index_exists: bool