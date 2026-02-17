from datetime import UTC, datetime
from typing import Any

from ram_miner.utils.extract import get_brand_id, get_store_id
from ram_miner.utils.processing import (
    prepare_brand_record,
    prepare_hardware_record,
    prepare_inventory_record,
    prepare_listing_record,
    prepare_pricing_record,
    prepare_store_record,
)


def _process_store_record(
    item: dict[str, Any], store_id: int, seen_store_ids: set[int]
) -> dict[str, Any]:
    if store_id in seen_store_ids:
        return {}
    record = prepare_store_record(item, store_id)
    record["timestamp"] = datetime.now(UTC).isoformat()
    seen_store_ids.add(store_id)
    return record


def _process_brand_record(
    item: dict[str, Any], brand_id: int, seen_brand_ids: set[int]
) -> dict[str, Any]:
    if brand_id in seen_brand_ids:
        return {}
    record = prepare_brand_record(item, brand_id)
    record["timestamp"] = datetime.now(UTC).isoformat()
    seen_brand_ids.add(brand_id)
    return record


def _process_hardware_record(
    item: dict[str, Any],
    clean_mpn: str | None,
    clean_ean: str | None,
    brand_id: int,
    seen_hardware_mpns: set[str],
) -> dict[str, Any]:
    if not clean_mpn or clean_mpn in seen_hardware_mpns:
        return {}
    record = prepare_hardware_record(item, clean_mpn, clean_ean, brand_id)
    seen_hardware_mpns.add(clean_mpn)
    return record


def _process_listing_record(
    item: dict[str, Any],
    store_id: int,
    clean_mpn: str | None,
    listing_key: tuple[int, str],
    seen_listings: set[tuple[int, str]],
) -> dict[str, Any]:
    if listing_key in seen_listings:
        return {}
    record = prepare_listing_record(item, store_id, clean_mpn)
    seen_listings.add(listing_key)
    return record


def _process_pricing_record(
    item: dict[str, Any],
    store_id: int,
    listing_key: tuple[int, str],
    latest_prices: dict[tuple[int, str], float | None],
) -> dict[str, Any]:
    record = prepare_pricing_record(item, store_id)
    new_price = record.get("price")
    if listing_key not in latest_prices or latest_prices.get(listing_key) != new_price:
        latest_prices[listing_key] = new_price
        return record
    return {}


def _process_inventory_record(
    item: dict[str, Any],
    store_id: int,
    listing_key: tuple[int, str],
    latest_inventory: dict[tuple[int, str], tuple[Any, ...]],
) -> dict[str, Any]:
    record = prepare_inventory_record(item, store_id)
    new_inv_state = (
        record.get("stock_store"),
        record.get("stock_supplier"),
        record.get("availability"),
    )
    if (
        listing_key not in latest_inventory
        or latest_inventory.get(listing_key) != new_inv_state
    ):
        latest_inventory[listing_key] = new_inv_state
        return record
    return {}


def prepare_all_records(
    item: dict[str, Any],
    normalized: dict[str, Any],
    seen_store_ids: set[int],
    seen_brand_ids: set[int],
    seen_hardware_mpns: set[str],
    seen_listings: set[tuple[int, str]],
    latest_prices: dict[tuple[int, str], float | None],
    latest_inventory: dict[tuple[int, str], tuple[Any, ...]],
) -> dict[str, dict[str, Any]]:
    store_id = get_store_id(normalized["store_name"])
    brand_id = get_brand_id(normalized["brand_name"])
    clean_mpn = normalized["mpn"]
    clean_ean = normalized["ean"]
    sku = normalized["sku"]
    listing_key = (store_id, sku)

    return {
        "stores": _process_store_record(item, store_id, seen_store_ids),
        "brands": _process_brand_record(item, brand_id, seen_brand_ids),
        "hardware": _process_hardware_record(
            item, clean_mpn, clean_ean, brand_id, seen_hardware_mpns
        ),
        "listings": _process_listing_record(
            item, store_id, clean_mpn, listing_key, seen_listings
        ),
        "prices": _process_pricing_record(item, store_id, listing_key, latest_prices),
        "inventory": _process_inventory_record(
            item, store_id, listing_key, latest_inventory
        ),
    }
