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
        "2. Si el contexto no contiene información suficiente, di: 'No encontré información "
        "suficiente en mis fuentes para responder esta pregunta.'\n"
        "3. Usa lenguaje sencillo, apropiado para agricultores.\n"
        "4. Al final de tu respuesta, indica las fuentes que usaste.\n"
        "5. No inventes datos, cifras ni recomendaciones que no estén en el contexto."
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
            f"Da una respuesta detallada basada en el contexto. Cita las fuentes."
        )

    return system_prompt, user_prompt
