from __future__ import annotations
import re

_PLATE = re.compile(r"^[A-Z0-9]{4,16}$")


def normalize_plate(value: str) -> str:
    """Normalize OCR/manual input without claiming country-specific validity."""
    normalized = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    if not _PLATE.fullmatch(normalized):
        raise ValueError("Registration number must contain 4–16 letters or digits.")
    return normalized


def display_plate(normalized: str) -> str:
    """Keep a readable display value while matching on the normalized value."""
    return normalized
