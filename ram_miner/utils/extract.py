import re


def extract_int(text: str) -> int | None:
    """Helper to extract the first integer from a string (e.g. '32 GB' -> 32)."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None
