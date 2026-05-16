"""
AgroChat — Crop detector.
Detects which crop(s) the user is asking about from the query text.
Uses keyword matching first, falls back to 'all crops' if none detected.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Keywords mapped to crop labels (as stored in FAISS metadata)
CROP_KEYWORDS: dict[str, list[str]] = {
    "café": ["café", "cafe", "coffee", "cafetal", "cafeto", "caficultura", "broca", "roya"],
    "cacao": ["cacao", "cocoa", "chocolate", "mazorca", "monilia", "carmenta", "theobroma"],
    "aguacate": ["aguacate", "avocado", "hass", "persea"],
    "banano": ["banano", "banana", "plátano", "platano", "musaceae", "sigatoka"],
    "maíz": ["maíz", "maiz", "corn", "elote", "mazorca de maíz", "zea mays"],
    "arroz": ["arroz", "rice", "oryza", "arrozal", "paddy"],
}


def detect_crops(query: str) -> list[str]:
    """
    Detect which crop(s) are mentioned in the query.

    Args:
        query: User question in any language.

    Returns:
        List of crop labels detected (e.g., ["café", "cacao"]).
        Empty list means no specific crop detected (search all).
    """
    query_lower = query.lower()
    detected = []

    for crop_label, keywords in CROP_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                detected.append(crop_label)
                break

    if detected:
        logger.info("Detected crops in query: %s", detected)
    else:
        logger.info("No specific crop detected, searching all.")

    return detected