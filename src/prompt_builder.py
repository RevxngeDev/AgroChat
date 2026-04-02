"""
AgroChat MVP — Prompt builder.
Constructs the final LLM prompt from system instructions,
retrieved context chunks, and the user query.
"""

from src.languages import get_lang_pack
from src.retriever import RetrievedChunk


def build_prompt(query: str, chunks: list[RetrievedChunk], lang: str = "es") -> tuple[str, str]:
    """
    Build system and user prompts for the LLM.

    Args:
        query: The user's question.
        chunks: Retrieved context chunks.
        lang: Language code ('es', 'ru', ...).

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    lang_pack = get_lang_pack(lang)
    system_prompt = lang_pack["system_prompt"]

    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Fuente {i}: {chunk.source_file} | Cultivo: {chunk.crop} | Pág: {chunk.page_label}]\n"
            f"{chunk.text}"
        )
    context_block = "\n\n---\n\n".join(context_parts)

    user_prompt = (
        f"{lang_pack['context_label']}:\n{context_block}\n\n"
        f"{lang_pack['question_label']}: {query}\n\n"
        f"{lang_pack['user_instruction']}"
    )

    return system_prompt, user_prompt