# Utilities for cleaning and normalizing scraped fields
from __future__ import annotations

import re

MODULES_PATTERN = re.compile(
    r"(?P<count>\d+)\s*[xX]\s*(?P<capacity>\d+)\s*(?:GB|G[Bb])"
)

SYSTEM_DESKTOP = {"pc", "desktop", "tower"}
SYSTEM_LAPTOP = {"laptop", "notebook", "ultrabook"}


def parse_modules(raw: str | None) -> tuple[int | None, int | None]:
    """Parse a raw modules string like '2x16GB' into (count, per_module_capacity_gb).

    Returns (None, None) when parsing fails or input is empty.
    Examples:
        '2x16GB' -> (2, 16)
        '4x8 GB' -> (4, 8)
    """
    if not raw:
        return None, None
    m = MODULES_PATTERN.search(raw)
    if not m:
        return None, None
    try:
        return int(m.group("count")), int(m.group("capacity"))
    except Exception:
        return None, None


def normalize_system(raw: str | None) -> str | None:
    """Normalize system-of-usage labels to 'desktop' or 'laptop'.

    Returns None when input is empty or cannot be classified.
    """
    if not raw:
        return None
    s = raw.strip().lower()
    if s in SYSTEM_DESKTOP:
        return "desktop"
    if s in SYSTEM_LAPTOP:
        return "laptop"
    # Heuristics: substring checks
    if any(k in s for k in ("pc", "desktop", "tower")):
        return "desktop"
    if any(k in s for k in ("laptop", "notebook", "ultrabook")):
        return "laptop"
    return None
