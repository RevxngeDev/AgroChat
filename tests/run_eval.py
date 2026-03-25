"""
AgroChat MVP — Batch evaluation runner.
Uses the same RAG pipeline as rag_cli.py, but reads questions from CSV
and saves outputs to CSV + JSONL for later analysis in Excel.

Usage:
    python -m src.run_eval --version v0.1
"""

import argparse
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import track

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
            RichHandler(console=console, rich_tracebacks=True, show_path=False),
            logging.FileHandler(config.LOG_DIR / "run_eval.log", encoding="utf-8"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AgroChat batch evaluation")
    parser.add_argument("--input", default="tests/questions.csv", help="CSV file with evaluation questions")
    parser.add_argument("--results-dir", default="tests/results", help="Directory to save CSV/JSONL results")
    parser.add_argument("--version", default="v0.1", help="Version label for this evaluation run")
    parser.add_argument("--lang", choices=["es", "ru"], default=config.DEFAULT_LANG, help="Response language")
    parser.add_argument("--model", default=config.LLM_MODEL, help="Groq model name")
    parser.add_argument("--top-k", type=int, default=config.TOP_K, help="Number of chunks to retrieve")
    return parser.parse_args()


def read_questions(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Questions file not found: {path}")

    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("active", "1")).strip() == "1":
                rows.append(row)
    return rows


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def flatten_sources(sources: list[dict]) -> tuple[str, str, str, str]:
    files = []
    crops = []
    pages = []
    scores = []

    for src in sources:
        files.append(str(src.get("file", "")))
        crops.append(str(src.get("crop", "")))
        pages.append(str(src.get("page", "")))

        score = src.get("score", "")
        if isinstance(score, (int, float)):
            scores.append(f"{score:.4f}")
        else:
            scores.append(str(score))

    return (
        " | ".join(files),
        " | ".join(crops),
        " | ".join(pages),
        " | ".join(scores),
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return

    fieldnames = [
        "timestamp",
        "version",
        "test_id",
        "question",
        "crop",
        "type",
        "expected_topic",
        "lang",
        "model",
        "top_k",
        "elapsed_sec",
        "chunks_found",
        "num_sources",
        "answered",
        "response",
        "retrieved_files",
        "retrieved_crops",
        "retrieved_pages",
        "retrieved_scores",
        "manual_score_1_to_5",
        "retrieval_ok_yes_no",
        "concept_confusion_yes_no",
        "hallucination_yes_no",
        "notes",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    setup_logging()
    logger = logging.getLogger("run_eval")
    args = parse_args()

    warnings = config.validate()
    for w in warnings:
        console.print(f"[yellow]Warning:[/yellow] {w}")
    if any("GROQ_API_KEY" in w for w in warnings):
        return

    input_path = Path(args.input)
    results_dir = Path(args.results_dir)
    ensure_dir(results_dir)

    questions = read_questions(input_path)
    if not questions:
        console.print("[red]No hay preguntas activas en el CSV.[/red]")
        return

    console.rule("[bold green]AgroChat — Batch Evaluation[/bold green]")
    console.print(f"Preguntas : {input_path}")
    console.print(f"Versión   : {args.version}")
    console.print(f"Idioma    : {args.lang}")
    console.print(f"Modelo    : {args.model}")
    console.print(f"Top-K     : {args.top_k}")
    console.print()

    try:
        index = load_index()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = results_dir / f"eval_{args.version}_{run_timestamp}.csv"
    jsonl_path = results_dir / f"eval_{args.version}_{run_timestamp}.jsonl"

    csv_rows = []
    jsonl_rows = []

    for row in track(questions, description="Ejecutando pruebas..."):
        test_id = str(row.get("test_id", "")).strip()
        question = str(row.get("question", "")).strip()
        crop = str(row.get("crop", "")).strip()
        qtype = str(row.get("type", "")).strip()
        expected_topic = str(row.get("expected_topic", "")).strip()

        try:
            start = time.time()

            logger.info("Test %s | Query: %s", test_id, question)

            chunks = retrieve(index, question, top_k=args.top_k)

            if not chunks:
                elapsed = time.time() - start
                csv_row = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "version": args.version,
                    "test_id": test_id,
                    "question": question,
                    "crop": crop,
                    "type": qtype,
                    "expected_topic": expected_topic,
                    "lang": args.lang,
                    "model": args.model,
                    "top_k": args.top_k,
                    "elapsed_sec": f"{elapsed:.2f}",
                    "chunks_found": 0,
                    "num_sources": 0,
                    "answered": "no",
                    "response": "No se encontraron fragmentos relevantes.",
                    "retrieved_files": "",
                    "retrieved_crops": "",
                    "retrieved_pages": "",
                    "retrieved_scores": "",
                    "manual_score_1_to_5": "",
                    "retrieval_ok_yes_no": "",
                    "concept_confusion_yes_no": "",
                    "hallucination_yes_no": "",
                    "notes": "",
                }
                csv_rows.append(csv_row)
                jsonl_rows.append(csv_row)
                continue

            system_prompt, user_prompt = build_prompt(question, chunks, lang=args.lang)
            answer = get_completion(system_prompt, user_prompt, model=args.model)
            rag_resp = build_response(answer, chunks, question, args.model, args.lang)

            elapsed = time.time() - start
            retrieved_files, retrieved_crops, retrieved_pages, retrieved_scores = flatten_sources(rag_resp.sources)

            csv_row = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "version": args.version,
                "test_id": test_id,
                "question": question,
                "crop": crop,
                "type": qtype,
                "expected_topic": expected_topic,
                "lang": args.lang,
                "model": args.model,
                "top_k": args.top_k,
                "elapsed_sec": f"{elapsed:.2f}",
                "chunks_found": len(chunks),
                "num_sources": len(rag_resp.sources),
                "answered": "yes" if rag_resp.answer else "no",
                "response": rag_resp.answer,
                "retrieved_files": retrieved_files,
                "retrieved_crops": retrieved_crops,
                "retrieved_pages": retrieved_pages,
                "retrieved_scores": retrieved_scores,
                "manual_score_1_to_5": "",
                "retrieval_ok_yes_no": "",
                "concept_confusion_yes_no": "",
                "hallucination_yes_no": "",
                "notes": "",
            }

            jsonl_row = {
                **csv_row,
                "sources_full": rag_resp.sources,
            }

            csv_rows.append(csv_row)
            jsonl_rows.append(jsonl_row)
            logger.info("Test %s completed in %.2fs", test_id, elapsed)

        except Exception as e:
            logger.exception("Test %s failed", test_id)

            csv_row = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "version": args.version,
                "test_id": test_id,
                "question": question,
                "crop": crop,
                "type": qtype,
                "expected_topic": expected_topic,
                "lang": args.lang,
                "model": args.model,
                "top_k": args.top_k,
                "elapsed_sec": "",
                "chunks_found": 0,
                "num_sources": 0,
                "answered": "no",
                "response": f"ERROR: {e}",
                "retrieved_files": "",
                "retrieved_crops": "",
                "retrieved_pages": "",
                "retrieved_scores": "",
                "manual_score_1_to_5": "",
                "retrieval_ok_yes_no": "",
                "concept_confusion_yes_no": "",
                "hallucination_yes_no": "",
                "notes": "",
            }

            csv_rows.append(csv_row)
            jsonl_rows.append(csv_row)

    write_csv(csv_path, csv_rows)
    write_jsonl(jsonl_path, jsonl_rows)

    console.print()
    console.print(f"[green]CSV guardado en:[/green] {csv_path}")
    console.print(f"[green]JSONL guardado en:[/green] {jsonl_path}")
    console.rule("[bold green]Evaluación terminada[/bold green]")


if __name__ == "__main__":
    main()