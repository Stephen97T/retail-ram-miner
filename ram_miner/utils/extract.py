import re
from typing import Any

from ram_miner.utils.cleaning import normalize_system, parse_modules


def extract_int(text: str) -> int | None:
    """Helper to extract the first integer from a string (e.g. '32 GB' -> 32)."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def calculate_price_per_gb(
    price: int | float | str | None, capacity_gb: int | str | None
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


def _get_azerty_mapping() -> dict[str, tuple[str, Any]]:
    """Returns the mapping of target fields to (dutch_key, processing_function)."""
    return {
        "capacity_gb": ("intern geheugen", extract_int),
        "clock_speed": ("kloksnelheid geheugen", extract_int),
        "transfer_speed": ("overdrachtssnelheid geheugengegevens", extract_int),
        "latency": ("cas-latentie", extract_int),
        "generation": ("intern geheugentype", None),
        "brand": ("merk", None),
        "sku": ("artikelnummer", None),
        "mpn": ("fabrikantcode", None),
        "ean": ("ean", None),
        "system_of_usage": ("component voor", normalize_system),
        "modules": ("geheugenlayout (modules x formaat)", None),
    }


# Note: Ideally this would be in a spider-specific file or the spider itself,
# but per instructions we move logic here.
def extract_azerty_specs(response: Any) -> dict[str, Any]:
    """
    Extract technical specifications from Azerty product page used to populate RamItem.
    Returns a dictionary of raw/cleaned values.
    """
    # 1. Get mappings
    field_mappings = _get_azerty_mapping()

    # 2. Scrape raw specs into a dictionary
    specs_table = response.css("table tr")
    raw_specs = {}
    for row in specs_table:
        key = row.css("th::text, dt::text").get(default="").strip().lower()
        val = row.css("td::text, dd::text").get(default="").strip()
        if key:
            raw_specs[key] = val

    specs = {}
    for field, (source_key, processor) in field_mappings.items():
        value = raw_specs.get(source_key)
        if processor and value:
            specs[field] = processor(value)
        else:
            specs[field] = value

    # 3. Handle complex/dependent fields
    module_count, module_cap = parse_modules(specs.get("modules"))
    specs["modules_count"] = module_count
    specs["module_capacity_gb"] = module_cap

    return specs
