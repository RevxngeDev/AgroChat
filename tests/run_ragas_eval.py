import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import track
from openai import OpenAI
from ragas.llms import llm_factory

from src import config
from src.indexer import load_index
from src.query_normalizer import normalize_query_for_retrieval
from src.retriever import retrieve
from src.services.query_service import run_query

console = Console()

DEFAULT_MODELS = [
    "openai/gpt-oss-20b",
]


def setup_logging() -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True, show_path=False),
            logging.FileHandler(config.LOG_DIR / "run_ragas_eval.log", encoding="utf-8"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation for AgroChat")
    parser.add_argument(
        "--input",
        default="tests/eval_dataset.json",
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument(
        "--results-dir",
        default="tests/results/ragas",
        help="Directory to save outputs",
    )
    parser.add_argument(
        "--lang",
        default="es",
        choices=["es", "ru", "en"],
        help="Response language for evaluation",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=config.TOP_K,
        help="Retriever top-k",
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=DEFAULT_MODELS,
        help="Models to evaluate",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=8.0,
        help="Delay in seconds between requests",
    )
    return parser.parse_args()


def load_eval_dataset(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Evaluation dataset must be a JSON list.")

    clean_rows = []
    for i, row in enumerate(data, start=1):
        question = str(row.get("question", "")).strip()
        ground_truth = str(row.get("ground_truth", "")).strip()
        crop = str(row.get("crop", "")).strip() or "unknown"

        if not question or not ground_truth:
            continue

        clean_rows.append(
            {
                "test_id": i,
                "question": question,
                "ground_truth": ground_truth,
                "crop": crop,
                "source_file": str(row.get("source_file", "")).strip(),
                "page": str(row.get("page", "")).strip(),
            }
        )

    return clean_rows


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_contexts_for_question(index, question: str, lang: str, top_k: int) -> tuple[str, list[str]]:
    retrieval_query = normalize_query_for_retrieval(question, lang)
    chunks = retrieve(index, retrieval_query, top_k=top_k)

    contexts = []
    for chunk in chunks:
        context_text = (
            f"FILE: {chunk.source_file}\n"
            f"CROP: {chunk.crop}\n"
            f"PAGE: {chunk.page_label}\n"
            f"TEXT:\n{chunk.text}"
        )
        contexts.append(context_text)

    return retrieval_query, contexts


def build_ragas_dataset(rows: list[dict]) -> Dataset:
    records = []
    for row in rows:
        answer = str(row.get("answer", "")).strip()
        if not answer or answer.startswith("ERROR:"):
            continue

        contexts = row.get("contexts", [])
        if not isinstance(contexts, list):
            contexts = []

        records.append(
            {
                "question": row["question"],
                "answer": answer,
                "contexts": contexts,
                "ground_truth": row["ground_truth"],
            }
        )

    return Dataset.from_list(records)


def evaluate_one_model(index, questions: list[dict], model_name: str, lang: str, top_k: int, delay: float):
    logger = logging.getLogger(f"ragas_eval.{model_name}")
    detailed_rows = []

    for row in track(questions, description=f"Evaluating {model_name}"):
        question = row["question"]

        try:
            result = run_query(
                index=index,
                question=question,
                lang=lang,
                model=model_name,
                top_k=top_k,
                user_id=None,
            )

            retrieval_query, contexts = get_contexts_for_question(
                index=index,
                question=question,
                lang=lang,
                top_k=top_k,
            )

            detailed_rows.append(
                {
                    "test_id": row["test_id"],
                    "crop": row["crop"],
                    "source_file": row["source_file"],
                    "page": row["page"],
                    "question": row["question"],
                    "ground_truth": row["ground_truth"],
                    "answer": result.answer,
                    "contexts": contexts,
                    "retrieval_query": retrieval_query,
                    "sources": result.sources,
                    "model": model_name,
                    "lang": result.lang,
                    "elapsed_sec": result.elapsed_sec,
                    "chunks_found": result.chunks_found,
                }
            )

        except Exception as e:
            logger.exception("Failed question test_id=%s", row["test_id"])
            detailed_rows.append(
                {
                    "test_id": row["test_id"],
                    "crop": row["crop"],
                    "source_file": row["source_file"],
                    "page": row["page"],
                    "question": row["question"],
                    "ground_truth": row["ground_truth"],
                    "answer": f"ERROR: {e}",
                    "contexts": [],
                    "retrieval_query": "",
                    "sources": [],
                    "model": model_name,
                    "lang": lang,
                    "elapsed_sec": None,
                    "chunks_found": 0,
                }
            )

        time.sleep(delay)

    ragas_dataset = build_ragas_dataset(detailed_rows)
    if len(ragas_dataset) == 0:
        raise RuntimeError(f"No valid rows to evaluate for model {model_name}")

    judge_client = OpenAI(
        api_key=config.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

    evaluator_llm = llm_factory(
        "llama-3.1-8b-instant",
        client=judge_client,
        provider="openai",
    )

    ragas_result = evaluate(
        dataset=ragas_dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=evaluator_llm,
        raise_exceptions=False,
    )

    ragas_df = ragas_result.to_pandas().reset_index(drop=True)
    details_df = pd.DataFrame(detailed_rows).reset_index(drop=True)

    valid_details_df = details_df[~details_df["answer"].astype(str).str.startswith("ERROR:")].reset_index(drop=True)
    merged_df = pd.concat([valid_details_df, ragas_df], axis=1)

    latency_series = pd.to_numeric(details_df["elapsed_sec"], errors="coerce").dropna()
    avg_latency = round(latency_series.mean(), 2) if not latency_series.empty else None

    summary = {
        "model": model_name,
        "questions_total": len(details_df),
        "questions_evaluated": len(ragas_df),
        "faithfulness": round(float(ragas_df["faithfulness"].mean()), 4),
        "answer_relevancy": round(float(ragas_df["answer_relevancy"].mean()), 4),
        "context_precision": round(float(ragas_df["context_precision"].mean()), 4),
        "context_recall": round(float(ragas_df["context_recall"].mean()), 4),
        "avg_latency_sec": avg_latency,
    }

    return summary, details_df, merged_df


def main() -> None:
    setup_logging()
    args = parse_args()

    warnings = config.validate()
    for w in warnings:
        console.print(f"[yellow]Warning:[/yellow] {w}")

    if any("GROQ_API_KEY" in w for w in warnings):
        console.print("[red]Missing GROQ_API_KEY.[/red]")
        return

    input_path = Path(args.input)
    results_dir = Path(args.results_dir)
    ensure_dir(results_dir)

    questions = load_eval_dataset(input_path)
    if not questions:
        console.print("[red]No valid questions found in eval dataset.[/red]")
        return

    console.rule("[bold green]AgroChat — RAGAS Evaluation[/bold green]")
    console.print(f"Dataset : {input_path}")
    console.print(f"Lang    : {args.lang}")
    console.print(f"Top-K   : {args.top_k}")
    console.print(f"Models  : {', '.join(args.models)}")
    console.print()

    try:
        index = load_index()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_rows = []

    for model_name in args.models:
        console.rule(f"[bold blue]Model: {model_name}[/bold blue]")

        summary, details_df, merged_df = evaluate_one_model(
            index=index,
            questions=questions,
            model_name=model_name,
            lang=args.lang,
            top_k=args.top_k,
            delay=args.delay,
        )

        safe_model_name = model_name.replace("/", "_")
        raw_path = results_dir / f"{run_id}_{safe_model_name}_raw.csv"
        ragas_path = results_dir / f"{run_id}_{safe_model_name}_ragas.csv"

        details_df_to_save = details_df.copy()
        details_df_to_save["contexts"] = details_df_to_save["contexts"].apply(
            lambda x: json.dumps(x, ensure_ascii=False)
        )
        details_df_to_save["sources"] = details_df_to_save["sources"].apply(
            lambda x: json.dumps(x, ensure_ascii=False)
        )

        merged_df_to_save = merged_df.copy()
        merged_df_to_save["contexts"] = merged_df_to_save["contexts"].apply(
            lambda x: json.dumps(x, ensure_ascii=False)
        )
        merged_df_to_save["sources"] = merged_df_to_save["sources"].apply(
            lambda x: json.dumps(x, ensure_ascii=False)
        )

        details_df_to_save.to_csv(raw_path, index=False, encoding="utf-8-sig")
        merged_df_to_save.to_csv(ragas_path, index=False, encoding="utf-8-sig")

        summary_rows.append(summary)

        console.print(f"[green]Saved raw results:[/green] {raw_path}")
        console.print(f"[green]Saved RAGAS results:[/green] {ragas_path}")
        console.print(f"[cyan]Summary:[/cyan] {summary}")

    summary_df = pd.DataFrame(summary_rows)
    summary_path = results_dir / f"{run_id}_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    console.rule("[bold green]Done[/bold green]")
    console.print(f"[green]Saved final summary:[/green] {summary_path}")


if __name__ == "__main__":
    main()