import re


def extract_int(text: str) -> int | None:
    """Helper to extract the first integer from a string (e.g. '32 GB' -> 32)."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def calculate_price_per_gb(
    price: float | str | None, capacity_gb: int | str | None
) -> float | None:
    """
    Calculates price per GB based on price and total capacity.
    Returns None if inputs are invalid or incomplete.
    """
    try:
        if capacity_gb and price and float(capacity_gb) > 0:
            return round(float(price) / float(capacity_gb), 4)
    except (ValueError, TypeError):
        pass
    return None
