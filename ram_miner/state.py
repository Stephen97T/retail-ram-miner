import os
from typing import Any

from ram_miner.utils.io import read_lines as _read_lines


def load_state(data_dir: str, bucket_name: str | None = None) -> dict[str, Any]:
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
    for record in _read_lines(os.path.join(data_dir, "stores.jsonl"), bucket_name):
        if "store_id" in record:
            state["seen_store_ids"].add(record["store_id"])
    # 2. Brands
    for record in _read_lines(os.path.join(data_dir, "brands.jsonl"), bucket_name):
        if "brand_id" in record:
            state["seen_brand_ids"].add(record["brand_id"])
    # 3. Hardware
    for record in _read_lines(os.path.join(data_dir, "hardware.jsonl"), bucket_name):
        if "mpn" in record and record["mpn"]:
            state["seen_hardware_mpns"].add(record["mpn"])
    # 4. Listings
    for record in _read_lines(os.path.join(data_dir, "listings.jsonl"), bucket_name):
        if "store_id" in record and "store_sku" in record:
            key = (record["store_id"], str(record["store_sku"]))
            state["seen_listings"].add(key)
    return state
