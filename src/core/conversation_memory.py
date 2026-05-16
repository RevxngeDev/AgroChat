"""
AgroChat — Conversation memory.
Stores recent Q&A pairs per user for context-aware follow-up questions.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_HISTORY = 3  # Keep last 3 exchanges per user


@dataclass
class Exchange:
    question: str
    answer: str


_memory: dict[int, list[Exchange]] = defaultdict(list)


def add_exchange(user_id: int, question: str, answer: str) -> None:
    """Store a Q&A exchange for a user."""
    history = _memory[user_id]
    history.append(Exchange(question=question, answer=answer))
    if len(history) > MAX_HISTORY:
        _memory[user_id] = history[-MAX_HISTORY:]
    logger.info("Stored exchange for user %d (history: %d)", user_id, len(_memory[user_id]))


def get_history(user_id: int) -> list[Exchange]:
    """Get conversation history for a user."""
    return _memory.get(user_id, [])


def clear_history(user_id: int) -> None:
    """Clear conversation history for a user."""
    _memory.pop(user_id, None)


def format_history_for_prompt(user_id: int) -> str:
    """Format conversation history as text for the LLM prompt."""
    history = get_history(user_id)
    if not history:
        return ""

    parts = []
    for ex in history:
        parts.append(f"User: {ex.question}\nAssistant: {ex.answer[:200]}")

    return "\n\n".join(parts)