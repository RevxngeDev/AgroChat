"""
AgroChat MVP — RAG CLI (online pipeline).
Interactive command-line interface for querying the agricultural knowledge base.

Usage:
    python -m src.rag_cli                          # defaults: es, llama-3.1-8b-instant
    python -m src.rag_cli --lang ru                # Russian output
    python -m src.rag_cli --model llama-3.3-70b-versatile --top-k 3
"""

import argparse
import logging
import time

from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src import config
from src.indexer import load_index
from src.retriever import retrieve
from src.prompt_builder import build_prompt
from src.llm_client import get_completion
from src.response_builder import build_response

console = Console()


def setup_logging() -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_DIR / "rag_cli.log", encoding="utf-8"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AgroChat — Agricultural RAG CLI")
    parser.add_argument("--lang", choices=["es", "ru"], default=config.DEFAULT_LANG,
                        help="Response language (default: es)")
    parser.add_argument("--model", default=config.LLM_MODEL,
                        help="Groq model name")
    parser.add_argument("--top-k", type=int, default=config.TOP_K,
                        help="Number of chunks to retrieve")
    return parser.parse_args()


def display_response(rag_resp, elapsed: float) -> None:
    """Render the RAG response with rich formatting."""
    # Answer panel
    console.print()
    console.print(Panel(
        Markdown(rag_resp.answer),
        title="[bold green]AgroChat — Respuesta[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    # Sources table
    if rag_resp.sources:
        table = Table(title="Fuentes consultadas", show_lines=False)
        table.add_column("Archivo", style="cyan")
        table.add_column("Cultivo", style="yellow")
        table.add_column("Página", justify="center")
        table.add_column("Score", justify="right", style="dim")

        for src in rag_resp.sources:
            table.add_row(
                src["file"],
                src["crop"],
                str(src["page"]),
                f"{src['score']:.4f}",
            )
        console.print(table)

    # Timing info
    console.print(f"  [dim]Model: {rag_resp.model} | Lang: {rag_resp.lang} | Time: {elapsed:.1f}s[/dim]\n")


def main() -> None:
    setup_logging()
    logger = logging.getLogger("rag_cli")
    args = parse_args()

    # Validate
    warnings = config.validate()
    for w in warnings:
        console.print(f"[yellow]Warning:[/yellow] {w}")
    if any("GROQ_API_KEY" in w for w in warnings):
        return

    console.rule("[bold green]AgroChat — Asistente Agrícola Inteligente[/bold green]")
    console.print(f"  Idioma: {args.lang} | Modelo: {args.model} | Top-K: {args.top_k}")
    console.print("  Escribe tu pregunta (o 'salir' para terminar).\n")

    # Load index once
    try:
        index = load_index()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return

    # Interactive loop
    while True:
        try:
            query = console.input("[bold cyan]Pregunta:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not query or query.lower() in ("salir", "exit", "quit"):
            break

        start = time.time()

        # RAG pipeline
        logger.info("Query: %s", query)
        chunks = retrieve(index, query, top_k=args.top_k)

        if not chunks:
            console.print("[yellow]No se encontraron fragmentos relevantes.[/yellow]\n")
            continue

        system_prompt, user_prompt = build_prompt(query, chunks, lang=args.lang)
        answer = get_completion(system_prompt, user_prompt, model=args.model)
        rag_resp = build_response(answer, chunks, query, args.model, args.lang)

        elapsed = time.time() - start
        display_response(rag_resp, elapsed)
        logger.info("Response delivered in %.1fs", elapsed)


if __name__ == "__main__":
    main()
