import datetime
import re
from typing import Any

MODULES_PATTERN = re.compile(r"(?P<count>\d+)\s*[xX]\s*(?P<capacity>\d+)")

SYSTEM_DESKTOP = {"pc", "desktop", "tower"}
SYSTEM_LAPTOP = {"laptop", "notebook", "ultrabook"}


def clean_price(val: Any) -> float | None:
    """
    Cleans a price string and converts it to a float.
    Handles Dutch/EU formats like "€ 1.234,56" or "1.000,-".
    Also handles standard US formats if passed (though prioritizing , as decimal separator given context).
    """
    if val is None:
        return None
    if isinstance(val, (float, int)):
        return float(val)

    s = str(val).strip()
    if not s:
        return None

    s = s.replace("€", "").replace("EUR", "").strip()

    if s.endswith(",-"):
        s = s[:-2]
    elif s.endswith(".-"):
        s = s[:-2]

    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(".", "")

    try:
        return float(s)
    except ValueError:
        return None


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


def normalize_identifier(text: str | int | None) -> str | None:
    """
    Cleans MPNs and EANs to ensure they match between stores.
    1. Integers become strings.
    2. Whitespace stripped.
    3. Converted to uppercase.
    """
    if not text:
        return None
    return str(text).strip().upper()


def ensure_timestamp(item: dict[str, Any]) -> None:
    if not item.get("timestamp"):
        item["timestamp"] = datetime.datetime.now(datetime.UTC)
