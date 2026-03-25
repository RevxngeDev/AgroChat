"""
AgroChat MVP — Prompt builder.
Constructs the final LLM prompt from system instructions,
retrieved context chunks, and the user query.
"""

from src.retriever import RetrievedChunk

# System prompts per language
SYSTEM_PROMPTS: dict[str, str] = {
    "es": (
    "Eres AgroChat, un asistente agrícola inteligente especializado en cultivos de "
    "café y cacao en Colombia. Tu objetivo es dar recomendaciones prácticas, claras y "
    "confiables a agricultores.\n\n"
    "REGLAS:\n"
    "1. Responde ÚNICAMENTE con información que aparezca en el CONTEXTO proporcionado.\n"
    "2. Si el contexto no contiene información suficiente, di exactamente: "
    "'No encontré información suficiente en mis fuentes para responder esta pregunta.'\n"
    "3. Responde SOLO lo que se pregunta. No agregues temas no solicitados.\n"
    "4. Distingue correctamente entre plagas, enfermedades, clima, suelo, fertilización, "
    "manejo agronómico y poscosecha. No mezcles categorías.\n"
    "5. Si el contexto mezcla conceptos, acláralo explícitamente en la respuesta.\n"
    "6. Si la pregunta es comparativa, compara únicamente si hay información suficiente "
    "sobre ambos cultivos en el contexto. Si no la hay, dilo claramente.\n"
    "7. Usa lenguaje claro y práctico, apropiado para agricultores.\n"
    "8. Sé breve y enfocado. Prioriza listas cortas o puntos numerados cuando ayuden.\n"
    "9. No inventes datos, cifras ni recomendaciones que no estén en el contexto.\n"
    "10. Al final de la respuesta, incluye solo las fuentes realmente usadas."
    ),
    "ru": (
        "Ты AgroChat — интеллектуальный сельскохозяйственный ассистент, специализирующийся "
        "на выращивании кофе и какао в Колумбии. Твоя цель — давать практические, понятные "
        "и достоверные рекомендации фермерам.\n\n"
        "ПРАВИЛА:\n"
        "1. Отвечай ТОЛЬКО на основе информации из предоставленного КОНТЕКСТА.\n"
        "2. Если контекст не содержит достаточно информации, скажи: 'Я не нашёл достаточно "
        "информации в моих источниках для ответа на этот вопрос.'\n"
        "3. Используй простой язык, понятный фермерам.\n"
        "4. В конце ответа укажи использованные источники.\n"
        "5. Не выдумывай данные, цифры или рекомендации, которых нет в контексте."
    ),
}


def build_prompt(query: str, chunks: list[RetrievedChunk], lang: str = "es") -> tuple[str, str]:
    """
    Build system and user prompts for the LLM.

    Args:
        query: The user's question.
        chunks: Retrieved context chunks.
        lang: Language code ('es' or 'ru').

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    system_prompt = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["es"])

    # Build context block with source attribution
    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Fuente {i}: {chunk.source_file} | Cultivo: {chunk.crop} | Pág: {chunk.page_label}]\n"
            f"{chunk.text}"
        )
    context_block = "\n\n---\n\n".join(context_parts)

    if lang == "ru":
        user_prompt = (
            f"КОНТЕКСТ:\n{context_block}\n\n"
            f"ВОПРОС: {query}\n\n"
            f"Дай подробный ответ на основе контекста. Укажи источники."
        )
    else:
        user_prompt = (
        f"CONTEXTO:\n{context_block}\n\n"
        f"PREGUNTA: {query}\n\n"
        f"Responde de forma clara, breve y precisa basándote solo en el contexto. "
        f"No agregues información no pedida. Cita las fuentes utilizadas."
        )   

    return system_prompt, user_prompt
