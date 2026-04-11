"""
AgroChat — Generate evaluation dataset for RAGAS.

Improved version:
- Filters out low-quality chunks (bibliography, indexes, corrupted text)
- Balances questions per crop
- Validates question quality via LLM

Usage: python -m tests.generate_eval_dataset
"""

import json
import logging
import random
import re
from pathlib import Path

from rich.console import Console
from rich.progress import track

from src.indexer import load_index
from src.llm_client import get_completion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

# Target: 5 questions per crop
TARGET_PER_CROP = 5
TARGET_CROPS = ["café", "cacao"]
JUDGE_MODEL = "llama-3.3-70b-versatile"
OUTPUT_PATH = Path("tests/eval_dataset.json")

# Patterns that indicate a low-quality chunk
JUNK_PATTERNS = [
    r"\bcap[íi]tulo\s+\d+",            # table of contents
    r"\breferencias\b",                # bibliography section
    r"\bbibliograf[íi]a\b",
    r"https?://",                      # URLs (often bibliography)
    r"\b(19|20)\d{2}\)",               # citation year like (2015)
    r"\bisbn\b",
    r"\bdoi\b",
    r"\bissn\b",
    r"^\s*\d+\s*$",                    # only numbers
    r"\bet\s+al\.",                    # academic citations
    r"investigador\s+phd",             # bio sections
    r"actualmente\s+es\s+investigador",
]

QUESTION_GEN_PROMPT = """Eres un experto agrónomo creando preguntas de evaluación para un sistema RAG agrícola.

A partir del siguiente FRAGMENTO de un documento agrícola oficial sobre {crop}, genera UNA pregunta práctica que un agricultor real haría, junto con la respuesta correcta basada ÚNICAMENTE en el fragmento.

REGLAS ESTRICTAS:
1. La pregunta DEBE ser sobre conocimiento agrícola PRÁCTICO (manejo del cultivo, plagas, enfermedades, fertilización, riego, variedades, suelo, clima, cosecha, poscosecha).
2. La pregunta NO DEBE ser sobre: años de publicación, autores, capítulos del libro, biografías, instituciones, referencias bibliográficas.
3. La pregunta debe ser respondible 100% con la información del fragmento.
4. La pregunta debe sonar natural, como la haría un agricultor real.
5. La respuesta debe ser concisa (2-4 frases) y basarse SOLO en el fragmento.
6. Si el fragmento NO contiene información agrícola práctica útil, responde exactamente: {{"skip": true}}

FRAGMENTO:
{chunk_text}

Responde EXCLUSIVAMENTE en este formato JSON, sin texto adicional ni markdown:
{{
  "question": "pregunta aquí",
  "ground_truth": "respuesta correcta aquí"
}}"""


def is_junk_chunk(text: str) -> bool:
    """Detect low-quality chunks that won't produce useful questions."""
    text_lower = text.lower()

    # Too short
    if len(text.strip()) < 300:
        return True

    # Too many numbers / table-like content
    digit_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)
    if digit_ratio > 0.25:
        return True

    # Matches junk patterns
    junk_hits = sum(1 for pattern in JUNK_PATTERNS if re.search(pattern, text_lower))
    if junk_hits >= 2:
        return True

    # Too many special characters (corrupted PDF text)
    special_chars = sum(1 for c in text if c in "\\|_$*")
    if special_chars > len(text) * 0.05:
        return True

    return False


def get_chunks_by_crop(index, crop: str, n: int) -> list[dict]:
    """Sample n random non-junk chunks from a specific crop."""
    docstore = index.storage_context.docstore
    all_node_ids = list(docstore.docs.keys())
    random.shuffle(all_node_ids)

    chunks = []
    for node_id in all_node_ids:
        if len(chunks) >= n:
            break

        node = docstore.docs[node_id]
        meta = node.metadata or {}

        if meta.get("crop") != crop:
            continue

        text = node.get_content()
        if is_junk_chunk(text):
            continue

        chunks.append({
            "text": text,
            "crop": crop,
            "source_file": meta.get("source_file", "unknown"),
            "page_label": meta.get("page_label", "?"),
        })

    return chunks


def generate_qa_pair(chunk: dict) -> dict | None:
    """Use the LLM to generate a Q&A pair from a chunk."""
    prompt = QUESTION_GEN_PROMPT.format(
        chunk_text=chunk["text"][:2000],
        crop=chunk["crop"],
    )

    try:
        response = get_completion(
            system_prompt="Eres un experto en generar preguntas de evaluación agrícola.",
            user_prompt=prompt,
            model=JUDGE_MODEL,
        )

        # Clean markdown
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
            response = response.strip()

        qa = json.loads(response)

        # Skip if LLM marked it as not useful
        if qa.get("skip"):
            return None

        if "question" not in qa or "ground_truth" not in qa:
            return None

        return {
            "question": qa["question"],
            "ground_truth": qa["ground_truth"],
            "source_chunk": chunk["text"],
            "crop": chunk["crop"],
            "source_file": chunk["source_file"],
            "page": chunk["page_label"],
        }
    except Exception as e:
        logger.warning("Failed to generate Q&A: %s", e)
        return None


def main() -> None:
    console.rule("[bold green]AgroChat — Generating balanced eval dataset[/bold green]")
    console.print(f"  Target: {TARGET_PER_CROP} questions per crop ({', '.join(TARGET_CROPS)})")
    console.print(f"  Model:  {JUDGE_MODEL}")
    console.print(f"  Output: {OUTPUT_PATH}\n")

    console.print("[bold]Loading FAISS index...[/bold]")
    index = load_index()

    all_qa = []

    for crop in TARGET_CROPS:
        console.print(f"\n[bold cyan]Processing crop: {crop}[/bold cyan]")

        # Oversample to account for rejections
        chunks = get_chunks_by_crop(index, crop, TARGET_PER_CROP * 4)
        console.print(f"  Found {len(chunks)} valid chunks")

        if not chunks:
            console.print(f"  [red]No valid chunks for {crop}, skipping[/red]")
            continue

        crop_qa = []
        for chunk in track(chunks, description=f"  Generating {crop}..."):
            if len(crop_qa) >= TARGET_PER_CROP:
                break
            qa = generate_qa_pair(chunk)
            if qa:
                crop_qa.append(qa)

        console.print(f"  [green]Generated {len(crop_qa)} questions for {crop}[/green]")
        all_qa.extend(crop_qa)

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(all_qa, f, ensure_ascii=False, indent=2)

    console.rule(f"[bold green]Done! Generated {len(all_qa)} Q&A pairs[/bold green]")
    console.print(f"  Saved to: {OUTPUT_PATH}\n")

    # Preview all questions
    console.print("[bold]Preview of all questions:[/bold]\n")
    for i, qa in enumerate(all_qa, 1):
        console.print(f"  [cyan]{i}. [{qa['crop']}][/cyan] {qa['source_file']} (p.{qa['page']})")
        console.print(f"     [yellow]Q:[/yellow] {qa['question']}")
        console.print(f"     [green]A:[/green] {qa['ground_truth'][:120]}...\n")


if __name__ == "__main__":
    main()