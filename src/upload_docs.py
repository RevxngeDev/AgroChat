"""
AgroChat MVP — Upload existing PDFs to Supabase.
Scans data/docs/<crop>/ folders, uploads each PDF to Storage,
and registers it in the documents table.

Usage: python -m src.upload_docs
"""

import logging
import sys

from rich.console import Console
from rich.table import Table

from src import config
from src.db.supabase_client import (
    get_crop_by_name,
    get_all_documents,
    register_document,
    upload_pdf,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()


def main() -> None:
    console.rule("[bold green]AgroChat — Upload PDFs to Supabase[/bold green]")

    # Get already registered files to avoid duplicates
    existing_docs = get_all_documents()
    existing_files = {(d["crops"]["name"], d["file_name"]) for d in existing_docs}

    uploaded = 0
    skipped = 0
    errors = 0

    for folder_name in config.CROP_FOLDERS:
        folder_path = config.DOCS_DIR / folder_name
        if not folder_path.exists():
            console.print(f"[yellow]Folder not found: {folder_path}[/yellow]")
            continue

        crop = get_crop_by_name(folder_name)
        if not crop:
            console.print(f"[red]Crop '{folder_name}' not found in database[/red]")
            continue

        pdf_files = sorted(folder_path.glob("*.pdf"))
        console.print(f"\n[bold]{folder_name}[/bold]: {len(pdf_files)} PDF(s) found")

        for pdf_path in pdf_files:
            file_name = pdf_path.name

            # Skip if already registered
            if (folder_name, file_name) in existing_files:
                console.print(f"  [dim]Skipped (already exists): {file_name}[/dim]")
                skipped += 1
                continue

            try:
                # Upload to Storage
                storage_path = f"{folder_name}/{file_name}"
                file_bytes = pdf_path.read_bytes()
                upload_pdf(storage_path, file_bytes)

                # Register in database
                register_document(
                    crop_id=crop["id"],
                    file_name=file_name,
                    storage_path=storage_path,
                )

                console.print(f"  [green]Uploaded: {file_name}[/green]")
                uploaded += 1

            except Exception as e:
                console.print(f"  [red]Error uploading {file_name}: {e}[/red]")
                errors += 1

    # Summary
    console.print()
    console.rule("[bold green]Done[/bold green]")
    console.print(f"  Uploaded: {uploaded}")
    console.print(f"  Skipped:  {skipped}")
    console.print(f"  Errors:   {errors}")

    # Show all documents in DB
    all_docs = get_all_documents()
    if all_docs:
        console.print()
        table = Table(title="Documents in Supabase")
        table.add_column("Crop", style="yellow")
        table.add_column("File", style="cyan")
        table.add_column("Indexed", justify="center")

        for doc in all_docs:
            table.add_row(
                doc["crops"]["label"],
                doc["file_name"],
                "✅" if doc["is_indexed"] else "❌",
            )
        console.print(table)


if __name__ == "__main__":
    main()