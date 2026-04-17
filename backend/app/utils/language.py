"""Simple language detection for Hindi vs English."""

import re

# Unicode range for Devanagari script
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def detect_language(text: str) -> str:
    """Detect if text is primarily Hindi or English. Returns 'hi' or 'en'."""
    devanagari_chars = len(_DEVANAGARI_RE.findall(text))
    if devanagari_chars > len(text) * 0.3:
        return "hi"
    return "en"
