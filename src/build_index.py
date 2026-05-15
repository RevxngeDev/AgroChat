"""
AgroChat MVP — Build index (incremental, Supabase-powered).
Downloads only unindexed PDFs from Supabase Storage,
processes them, adds to FAISS index, and cleans up.

Usage:  python -m src.build_index
"""

import logging
import sys
import tempfile
import time
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from src import config
from src.db.supabase_client import (
    get_unindexed_documents,
    download_pdf,
    mark_document_indexed,
)
from src.core.indexer import add_to_index, get_embed_model

console = Console()


def setup_logging() -> None:
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

    warnings = config.validate()
    for w in warnings:
        logger.warning(w)

    console.rule("[bold green]AgroChat — Incremental FAISS indexing[/bold green]")

    # Step 1: Check for unindexed documents
    console.print("[bold]Step 1/3:[/bold] Checking for unindexed documents...")
    unindexed = get_unindexed_documents()

    if not unindexed:
        console.print("[green]All documents are already indexed. Nothing to do.[/green]")
        return

    console.print(f"  Found {len(unindexed)} unindexed document(s):\n")
    for doc in unindexed:
        crop_label = doc["crops"]["label"] if doc.get("crops") else "?"
        console.print(f"    - {doc['file_name']} ({crop_label})")
    console.print()

    # Step 2: Download, parse, and collect documents
    console.print("[bold]Step 2/3:[/bold] Downloading and processing PDFs...")

    from llama_index.core import Document
    from llama_index.readers.file import PDFReader

    reader = PDFReader()
    all_docs: list[Document] = []
    processed_ids: list[int] = []

    for doc_record in unindexed:
        file_name = doc_record["file_name"]
        storage_path = doc_record["storage_path"]
        crop_label = doc_record["crops"]["label"] if doc_record.get("crops") else "unknown"
        crop_name = doc_record["crops"]["name"] if doc_record.get("crops") else "unknown"

        try:
            # Download to temp file
            pdf_bytes = download_pdf(storage_path)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = Path(tmp.name)

            # Parse PDF
            pages = reader.load_data(file=tmp_path)
            for page in pages:
                page.metadata.update({
                    "crop": crop_label,
                    "source_file": file_name,
                    "subfolder": crop_name,
                })
            all_docs.extend(pages)
            processed_ids.append(doc_record["id"])

            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

            console.print(f"  [green]Processed: {file_name} ({len(pages)} pages)[/green]")

        except Exception as e:
            console.print(f"  [red]Error processing {file_name}: {e}[/red]")
            logger.exception("Failed to process %s", file_name)

    if not all_docs:
        console.print("[red]No documents were processed successfully.[/red]")
        return

    console.print(f"\n  Total pages to index: {len(all_docs)}\n")

    # Step 3: Add to FAISS index
    console.print("[bold]Step 3/3:[/bold] Adding to FAISS index...")
    start = time.time()
    add_to_index(all_docs)
    elapsed = time.time() - start
    console.print(f"  Index updated in {elapsed:.1f}s\n")

    # Mark as indexed in Supabase
    for doc_id in processed_ids:
        mark_document_indexed(doc_id)

    # Summary
    console.rule("[bold green]Done![/bold green]")
    console.print(f"  Documents indexed: {len(processed_ids)}")
    console.print(f"  Total pages added: {len(all_docs)}")
    console.print(f"  Time: {elapsed:.1f}s\n")
    console.print("You can now run: [cyan]python -m src.rag_cli[/cyan]")


if __name__ == "__main__":
    main()