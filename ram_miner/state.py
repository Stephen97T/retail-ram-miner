import json
import os
from collections.abc import Iterator
from typing import Any


def load_lines(data_dir: str, filename: str) -> Iterator[dict[str, Any]]:
    fp = os.path.join(data_dir, filename)
    if os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)
        except Exception:
            # Logging should be handled by caller
            pass


def load_state(data_dir: str) -> dict[str, Any]:
    """
    Loads deduplication state from local files.
    Returns a dict with keys: seen_store_ids, seen_brand_ids, seen_hardware_mpns, seen_listings
    """
    state: dict[str, Any] = {
        "seen_store_ids": set(),
        "seen_brand_ids": set(),
        "seen_hardware_mpns": set(),
        "seen_listings": set(),
    }
    # 1. Stores
    for record in load_lines(data_dir, "stores.jsonl"):
        if "store_id" in record:
            state["seen_store_ids"].add(record["store_id"])
    # 2. Brands
    for record in load_lines(data_dir, "brands.jsonl"):
        if "brand_id" in record:
            state["seen_brand_ids"].add(record["brand_id"])
    # 3. Hardware
    for record in load_lines(data_dir, "hardware.jsonl"):
        if "mpn" in record and record["mpn"]:
            state["seen_hardware_mpns"].add(record["mpn"])
    # 4. Listings
    for record in load_lines(data_dir, "listings.jsonl"):
        if "store_id" in record and "store_sku" in record:
            key = (record["store_id"], str(record["store_sku"]))
            state["seen_listings"].add(key)
    return state
