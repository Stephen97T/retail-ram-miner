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


def clean_price(raw: str | None) -> float | None:
    """Clean price string allowing for Dutch format (1.000,00) or standard float."""
    if not raw:
        return None

    # Common cleanup
    s = (
        raw.replace("\u20ac", "")
        .replace("€", "")
        .replace(".-", "")
        .replace(",-", "")
        .strip()
    )

    # Heuristic: If it has comma, assume Dutch/EU format (comma decimal)
    # If it has dots and comma, assume Dutch (dot thousands, comma decimal)
    # If it has only dots, it depends.
    # Meta tags often use standard float (dot decimal).
    # UI text often uses Dutch (comma decimal, dot thousands).

    # To be safe against "1.299" (1299) vs "1.299" (1.299), we need context or assumptions.
    # For Azerty/Alternate in NL, UI is likely Dutch.

    # Detect check: if ',' in string, it's almost certainly decimal separator in NL context.
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # No comma.
        # If "1200", valid.
        # If "1.200", is it 1200 or 1.2? In NL price, likely 1200.
        # But if source is meta tag, it might be 1200.00
        # If we see multiple dots, it is thousands separators.
        if s.count(".") > 1:
            s = s.replace(".", "")
        elif "." in s:
            # Single dot. Check if it looks like thousands or float.
            # Usually prices don't have 3 decimals unless gas.
            # But "1.200" implies 1200. "12.50" implies 12.50.
            # Hard to distinguish "1.234" (1234) vs "1.234" (float).
            # Assuming if context is NL site text, dot is thousands.
            # But let's check if it matches float format.
            pass

    try:
        return float(s)
    except ValueError:
        return None


# Note: Ideally this would be in a spider-specific file or the spider itself,
# but per instructions we move logic here.
def extract_azerty_specs(response) -> dict:
    """
    Extract technical specifications from Azerty product page used to populate RamItem.
    Returns a dictionary of raw/cleaned values.
    """
    from ram_miner.utils.cleaning import parse_modules

    specs = {}

    # Broader selector: "table tr" covers tables without specific class.
    specs_table = response.css("table tr, dl.spec-list div")

    for row in specs_table:
        # Extract key/value pair (adjust selectors for th/td or dt/dd)
        key = row.css("th::text, dt::text").get(default="").strip().lower()
        val = row.css("td::text, dd::text").get(default="").strip()

        if not key or not val:
            continue

        # Map site-specific spec labels to dict fields
        if (
            "capaciteit" in key
            or "capacity" in key
            or ("intern geheugen" in key and "type" not in key)
        ):
            # e.g., "32 GB" -> 32
            specs["capacity_gb"] = extract_int(val)
        elif "snelheid" in key or "speed" in key or "overdracht" in key:
            # e.g., "6000 MHz" -> 6000
            # Logic to prefer highest value (Transfer Rate vs Clock) if multiple rows exist
            new_speed = extract_int(val)
            current_speed = specs.get("speed_mhz", 0)
            if new_speed and new_speed > current_speed:
                specs["speed_mhz"] = new_speed
        elif "geheugentype" in key or "technologie" in key:
            # e.g., "DDR5"
            specs["generation"] = val
        elif "latency" in key or "cas" in key:
            # e.g., "CL30" -> 30
            specs["latency"] = extract_int(val)
        elif "modules" in key or "kit" in key or "layout" in key:
            # e.g., "2 x 16 GB"
            specs["modules"] = val
            count, cap = parse_modules(val)
            specs["modules_count"] = count
            specs["module_capacity_gb"] = cap
        elif "component" in key or "gebruik" in key:
            from ram_miner.utils.cleaning import normalize_system

            specs["system_of_usage"] = normalize_system(val) or val
        # elif "voltage" in key: pass

    return specs
