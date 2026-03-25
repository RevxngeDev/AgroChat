"""
AgroChat MVP — Build index (offline pipeline).
Usage:  python -m src.build_index
"""

import logging
import sys
import time

from rich.console import Console
from rich.logging import RichHandler

from src import config
from src.loader import load_documents
from src.indexer import build_index

console = Console()


def setup_logging() -> None:
    """Configure structured logging to file + rich console."""
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True, show_path=False),
            logging.FileHandler(config.LOG_DIR / "build_index.log", encoding="utf-8"),
        ],
    )


def main() -> None:
    setup_logging()
    logger = logging.getLogger("build_index")

    # Validate configuration
    warnings = config.validate()
    for w in warnings:
        logger.warning(w)

    console.rule("[bold green]AgroChat — Building FAISS index[/bold green]")
    console.print(f"  Docs directory : {config.DOCS_DIR}")
    console.print(f"  Index directory: {config.INDEX_DIR}")
    console.print(f"  Embedding model: {config.EMBEDDING_MODEL}")
    console.print(f"  Chunk size     : {config.CHUNK_SIZE} (overlap {config.CHUNK_OVERLAP})")
    console.print()

    # Step 1: Load documents
    console.print("[bold]Step 1/2:[/bold] Loading PDFs...")
    docs = load_documents()
    if not docs:
        console.print("[red]No documents found. Check data/docs/ folder.[/red]")
        sys.exit(1)
    console.print(f"  Loaded {len(docs)} document pages.\n")

    # Step 2: Build and persist index
    console.print("[bold]Step 2/2:[/bold] Building index...")
    start = time.time()
    build_index(docs)
    elapsed = time.time() - start
    console.print(f"  Index built in {elapsed:.1f}s\n")

    console.rule("[bold green]Done![/bold green]")
    console.print("You can now run: [cyan]python -m src.rag_cli[/cyan]")


if __name__ == "__main__":
    main()
