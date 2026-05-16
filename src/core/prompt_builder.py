"""
AgroChat MVP — Prompt builder.
Constructs the final LLM prompt from system instructions,
retrieved context chunks, and the user query.
"""

from src.languages import get_lang_pack
from src.core.retriever import RetrievedChunk


def build_prompt(query: str, chunks: list[RetrievedChunk], lang: str = "es", conversation_history: str = "") -> tuple[str, str]:
    lang_pack = get_lang_pack(lang)

    system_prompt = (
        f"{lang_pack['system_prompt']}\n\n"
        f"{lang_pack['response_language_instruction']}\n\n"
        "ADDITIONAL OUTPUT RULES:\n"
        "1. Write the answer in a natural way for the user.\n"
        "2. Do NOT copy raw internal context tags such as [SOURCE ...], FILE, CROP, PAGE.\n"
        "3. Do NOT paste raw fragments from the context as source labels inside the answer.\n"
        "4. Use the context to answer, but paraphrase it naturally.\n"
        "5. If you mention sources, do it briefly and naturally, not by copying the raw tag format.\n"
        "6. Focus on the agricultural recommendation itself.\n"
    )

    if lang != "es":
        system_prompt += (
            f"\nCRITICAL LANGUAGE RULE:\n"
            f"The CONTEXT below is written in Spanish. You MUST translate and paraphrase "
            f"all information into {lang_pack['language_name']}. NEVER copy Spanish text "
            f"directly into your answer. Every word in your response must be in {lang_pack['language_name']}."
        )

    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[SOURCE {i} | FILE: {chunk.source_file} | CROP: {chunk.crop} | PAGE: {chunk.page_label}]\n"
            f"{chunk.text}"
        )

    context_block = "\n\n---\n\n".join(context_parts)
    
    history_block = ""
    if conversation_history:
        history_block = f"CONVERSATION HISTORY:\n{conversation_history}\n\n"

    user_prompt = (
        f"{history_block}"
        f"{lang_pack['context_label']}:\n{context_block}\n\n"
        f"{lang_pack['question_label']}: {query}\n\n"
        f"{lang_pack['user_instruction']}\n\n"
        "IMPORTANT:\n"
        "- Do not include raw source tags like [SOURCE ...] in the answer.\n"
        "- Do not mention FILE, CROP, or PAGE literally.\n"
        "- Answer naturally and clearly.\n"
    )

    if lang != "es":
        user_prompt += (
            f"\nREMINDER: {lang_pack['response_language_instruction']} "
            f"Do NOT include any Spanish text in your answer."
        )

    return system_prompt, user_prompt