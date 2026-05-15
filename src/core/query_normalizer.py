"""
AgroChat MVP — Query normalizer.
Normalizes user queries to the base corpus language (Spanish) before retrieval.
"""

import logging

from src.core.llm_client import get_completion

logger = logging.getLogger(__name__)

BASE_CORPUS_LANG = "es"


def normalize_query_for_retrieval(query: str, lang: str) -> str:
    """
    Normalize the user query to the base corpus language (Spanish) for retrieval.

    Rules:
    - If lang is already Spanish, return query unchanged.
    - If lang is English or Russian, translate only the query into Spanish.
    - Keep technical meaning unchanged.
    - Return only the translated query, with no explanations.
    """
    if not query.strip():
        return query

    if lang == BASE_CORPUS_LANG:
        return query

    system_prompt = (
        "Eres un traductor técnico agrícola.\n"
        "Tu única tarea es traducir consultas de usuarios al español.\n"
        "Reglas:\n"
        "1. Traduce solo la consulta.\n"
        "2. Conserva el sentido técnico y agrícola.\n"
        "3. No expliques nada.\n"
        "4. No agregues texto extra.\n"
        "5. Devuelve únicamente la consulta traducida al español."
    )

    user_prompt = f"Consulta original ({lang}): {query}"

    try:
        translated = get_completion(system_prompt, user_prompt)
        translated = translated.strip()
        if translated:
            logger.info("Query normalized to Spanish for retrieval: '%s' -> '%s'", query[:80], translated[:80])
            return translated
    except Exception as e:
        logger.warning("Failed to normalize query for retrieval, using original query. Error: %s", e)

    return query