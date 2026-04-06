"""
AgroChat MVP — Indexer.
Takes loaded documents, chunks them, generates embeddings,
builds a FAISS vector index, and persists it to disk.
"""

import logging
from pathlib import Path

import faiss
from llama_index.core import StorageContext, VectorStoreIndex, load_index_from_storage, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from src import config

logger = logging.getLogger(__name__)


def get_embed_model() -> HuggingFaceEmbedding:
    """Return the configured HuggingFace embedding model."""
    return HuggingFaceEmbedding(
        model_name=config.EMBEDDING_MODEL,
        local_files_only=True,
    )


def build_index(documents: list) -> VectorStoreIndex:
    """
    Build a FAISS-backed vector index from documents.

    Steps:
        1. Initialize FAISS flat index (L2 distance).
        2. Chunk documents with SentenceSplitter.
        3. Embed chunks and insert into FAISS.
        4. Persist index + docstore to disk.

    Args:
        documents: List of LlamaIndex Document objects.

    Returns:
        VectorStoreIndex ready for querying.
    """
    logger.info("Building FAISS index (dim=%d, chunk_size=%d, overlap=%d)",
                config.EMBEDDING_DIM, config.CHUNK_SIZE, config.CHUNK_OVERLAP)

    # 1. Create FAISS index
    faiss_index = faiss.IndexFlatL2(config.EMBEDDING_DIM)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 2. Configure chunking
    splitter = SentenceSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )

    # 3. Build index (chunks + embeds + inserts)
    Settings.embed_model = get_embed_model()

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=Settings.embed_model,
        transformations=[splitter],
        show_progress=True,
    )

    # 4. Persist to disk
    index_dir = config.INDEX_DIR
    index_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(index_dir))
    logger.info("Index persisted to %s", index_dir)

    return index


def load_index() -> VectorStoreIndex:
    """
    Load a previously persisted FAISS index from disk.

    Returns:
        VectorStoreIndex ready for querying.

    Raises:
        FileNotFoundError: If the index directory does not exist.
    """
    index_dir: Path = config.INDEX_DIR
    if not index_dir.exists():
        raise FileNotFoundError(
            f"Index not found at {index_dir}. Run build_index.py first."
        )

    logger.info("Loading FAISS index from %s", index_dir)

    # Forzar el mismo embedding usado al construir el índice
    Settings.embed_model = get_embed_model()

    vector_store = FaissVectorStore.from_persist_dir(str(index_dir))
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
        persist_dir=str(index_dir),
    )

    index = load_index_from_storage(storage_context=storage_context)

    logger.info("Index loaded successfully.")
    return index

def add_to_index(documents: list) -> VectorStoreIndex:
    """
    Add new documents to an existing FAISS index.
    If no index exists, creates one from scratch.

    Args:
        documents: List of new LlamaIndex Document objects to add.

    Returns:
        Updated VectorStoreIndex.
    """
    index_dir: Path = config.INDEX_DIR

    if index_dir.exists() and any(index_dir.iterdir()):
        logger.info("Loading existing index for incremental update...")
        index = load_index()

        splitter = SentenceSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
        nodes = splitter.get_nodes_from_documents(documents)

        logger.info("Adding %d new nodes to existing index", len(nodes))
        index.insert_nodes(nodes)

        index.storage_context.persist(persist_dir=str(index_dir))
        logger.info("Updated index persisted to %s", index_dir)
        return index
    else:
        logger.info("No existing index found. Building from scratch...")
        return build_index(documents)