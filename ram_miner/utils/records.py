from datetime import UTC, datetime
from typing import Any

from ram_miner.utils.processing import (
    prepare_brand_record,
    prepare_hardware_record,
    prepare_inventory_record,
    prepare_listing_record,
    prepare_pricing_record,
    prepare_store_record,
)


def prepare_all_records(
    item: dict[str, Any],
    normalized: dict[str, Any],
    seen_store_ids: set[int],
    seen_brand_ids: set[int],
    seen_hardware_mpns: set[str],
    seen_listings: set[tuple[int, str]],
    latest_prices: dict[tuple[int, str], float | None],
    latest_inventory: dict[tuple[int, str], tuple[Any, ...]],
    get_store_id,
    get_brand_id,
) -> dict[str, dict[str, Any]]:
    store_id = get_store_id(normalized["store_name"])
    brand_id = get_brand_id(normalized["brand_name"])
    clean_mpn = normalized["mpn"]
    clean_ean = normalized["ean"]
    sku = normalized["sku"]
    listing_key = (store_id, sku)
    # Store
    store_record = (
        prepare_store_record(item, store_id) if store_id not in seen_store_ids else {}
    )
    if store_record:
        store_record["timestamp"] = datetime.now(UTC).isoformat()
        seen_store_ids.add(store_id)
    # Brand
    brand_record = (
        prepare_brand_record(item, brand_id) if brand_id not in seen_brand_ids else {}
    )
    if brand_record:
        brand_record["timestamp"] = datetime.now(UTC).isoformat()
        seen_brand_ids.add(brand_id)
    # Hardware
    hardware_record = (
        prepare_hardware_record(item, clean_mpn, clean_ean, brand_id)
        if clean_mpn and clean_mpn not in seen_hardware_mpns
        else {}
    )
    if hardware_record:
        seen_hardware_mpns.add(clean_mpn)
    # Listing
    listing_record = (
        prepare_listing_record(item, store_id, clean_mpn)
        if listing_key not in seen_listings
        else {}
    )
    if listing_record:
        seen_listings.add(listing_key)
    # Pricing
    pricing_record = prepare_pricing_record(item, store_id)
    new_price = pricing_record.get("price")
    if listing_key not in latest_prices or latest_prices.get(listing_key) != new_price:
        latest_prices[listing_key] = new_price
    else:
        pricing_record = {}
    # Inventory
    inventory_record = prepare_inventory_record(item, store_id)
    new_inv_state = (
        inventory_record.get("stock_store"),
        inventory_record.get("stock_supplier"),
        inventory_record.get("availability"),
    )
    if (
        listing_key not in latest_inventory
        or latest_inventory.get(listing_key) != new_inv_state
    ):
        latest_inventory[listing_key] = new_inv_state
    else:
        inventory_record = {}
    return {
        "stores": store_record,
        "brands": brand_record,
        "hardware": hardware_record,
        "listings": listing_record,
        "prices": pricing_record,
        "inventory": inventory_record,
    }
