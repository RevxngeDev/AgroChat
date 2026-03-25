"""
AgroChat MVP — LLM client.
Sends the built prompt to Groq API and returns the raw completion.
"""

import logging

from groq import Groq

from src import config

logger = logging.getLogger(__name__)


def get_completion(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    """
    Call Groq API with the system + user prompt.

    Args:
        system_prompt: System instructions for the LLM.
        user_prompt: User message containing context + query.
        model: Override for the LLM model name.

    Returns:
        The LLM's text response.

    Raises:
        ValueError: If GROQ_API_KEY is not configured.
    """
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Check your .env file.")

    model_name = model or config.LLM_MODEL
    logger.info("Calling Groq API (model: %s)", model_name)

    client = Groq(api_key=config.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content or ""
    logger.info("LLM response received (%d chars)", len(answer))
    return answer
