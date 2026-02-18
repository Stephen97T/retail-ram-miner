from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ram_miner.utils.records import prepare_all_records


@pytest.fixture
def mock_dependencies() -> Iterator[dict[str, MagicMock]]:
    with (
        patch("ram_miner.utils.records.get_store_id") as mock_get_store_id,
        patch("ram_miner.utils.records.get_brand_id") as mock_get_brand_id,
        patch("ram_miner.utils.records.prepare_store_record") as mock_prepare_store,
        patch("ram_miner.utils.records.prepare_brand_record") as mock_prepare_brand,
        patch(
            "ram_miner.utils.records.prepare_hardware_record"
        ) as mock_prepare_hardware,
        patch("ram_miner.utils.records.prepare_listing_record") as mock_prepare_listing,
        patch("ram_miner.utils.records.prepare_pricing_record") as mock_prepare_pricing,
        patch(
            "ram_miner.utils.records.prepare_inventory_record"
        ) as mock_prepare_inventory,
    ):
        yield {
            "get_store_id": mock_get_store_id,
            "get_brand_id": mock_get_brand_id,
            "prepare_store": mock_prepare_store,
            "prepare_brand": mock_prepare_brand,
            "prepare_hardware": mock_prepare_hardware,
            "prepare_listing": mock_prepare_listing,
            "prepare_pricing": mock_prepare_pricing,
            "prepare_inventory": mock_prepare_inventory,
        }


def test_prepare_all_records_new_items(mock_dependencies: dict[str, MagicMock]) -> None:
    # Setup mocks
    mock_dependencies["get_store_id"].return_value = 1
    mock_dependencies["get_brand_id"].return_value = 10

    mock_dependencies["prepare_store"].return_value = {"store_id": 1, "name": "Store"}
    mock_dependencies["prepare_brand"].return_value = {"brand_id": 10, "name": "Brand"}
    mock_dependencies["prepare_hardware"].return_value = {"mpn": "MPN1", "specs": "..."}
    mock_dependencies["prepare_listing"].return_value = {"store_id": 1, "sku": "SKU1"}
    mock_dependencies["prepare_pricing"].return_value = {"price": 100.0}
    mock_dependencies["prepare_inventory"].return_value = {
        "stock_store": 5,
        "stock_supplier": 10,
        "availability": "In Stock",
    }

    # Inputs
    item: dict[str, Any] = {"some": "data"}
    normalized: dict[str, Any] = {
        "store_name": "Store",
        "brand_name": "Brand",
        "mpn": "MPN1",
        "ean": "EAN1",
        "sku": "SKU1",
    }
    seen_store_ids: set[int] = set()
    seen_brand_ids: set[int] = set()
    seen_hardware_mpns: set[str] = set()
    seen_listings: set[tuple[int, str]] = set()

    # Execute
    result = prepare_all_records(
        item,
        normalized,
        seen_store_ids,
        seen_brand_ids,
        seen_hardware_mpns,
        seen_listings,
    )

    # Assertions
    assert result["stores"]["store_id"] == 1
    assert result["brands"]["brand_id"] == 10
    assert result["hardware"]["mpn"] == "MPN1"
    assert result["listings"]["sku"] == "SKU1"
    assert result["prices"]["price"] == 100.0
    assert result["inventory"]["stock_store"] == 5

    # Check side effects (updates to sets/dicts)
    assert 1 in seen_store_ids
    assert 10 in seen_brand_ids
    assert "MPN1" in seen_hardware_mpns
    assert (1, "SKU1") in seen_listings


def test_prepare_all_records_deduplication(
    mock_dependencies: dict[str, MagicMock],
) -> None:
    # Setup mocks
    mock_dependencies["get_store_id"].return_value = 1
    mock_dependencies["get_brand_id"].return_value = 10

    # Pricing/Inventory should always return
    mock_dependencies["prepare_pricing"].return_value = {"price": 100.0}
    mock_dependencies["prepare_inventory"].return_value = {
        "stock_store": 5,
        "stock_supplier": 10,
        "availability": "In Stock",
    }

    # Inputs with existing data
    item: dict[str, Any] = {}
    normalized: dict[str, Any] = {
        "store_name": "Store",
        "brand_name": "Brand",
        "mpn": "MPN1",
        "ean": "EAN1",
        "sku": "SKU1",
    }
    seen_store_ids = {1}
    seen_brand_ids = {10}
    seen_hardware_mpns = {"MPN1"}
    seen_listings = {(1, "SKU1")}

    # Execute
    result = prepare_all_records(
        item,
        normalized,
        seen_store_ids,
        seen_brand_ids,
        seen_hardware_mpns,
        seen_listings,
    )

    # Assertions - everything should be empty/skipped for static data
    assert result["stores"] == {}
    assert result["brands"] == {}
    assert result["hardware"] == {}
    assert result["listings"] == {}
    # Price and inventory should always return regardless of previous state
    assert result["prices"] == {"price": 100.0}
    assert result["inventory"] == {
        "stock_store": 5,
        "stock_supplier": 10,
        "availability": "In Stock",
    }


def test_prepare_all_records_price_update(
    mock_dependencies: dict[str, MagicMock],
) -> None:
    # Setup mocks
    mock_dependencies["get_store_id"].return_value = 1
    mock_dependencies["get_brand_id"].return_value = 10

    # New price
    mock_dependencies["prepare_pricing"].return_value = {"price": 120.0}
    mock_dependencies["prepare_inventory"].return_value = {
        "stock_store": 5,
        "stock_supplier": 10,
        "availability": "In Stock",
    }

    # Inputs
    item: dict[str, Any] = {}
    normalized: dict[str, Any] = {
        "store_name": "Store",
        "brand_name": "Brand",
        "mpn": "MPN1",
        "ean": "EAN1",
        "sku": "SKU1",
    }
    seen_store_ids = {1}
    seen_brand_ids = {10}
    seen_hardware_mpns = {"MPN1"}
    seen_listings = {(1, "SKU1")}

    # Execute
    result = prepare_all_records(
        item,
        normalized,
        seen_store_ids,
        seen_brand_ids,
        seen_hardware_mpns,
        seen_listings,
    )

    # Assertions
    assert result["prices"]["price"] == 120.0
    # Inventory is always returned now
    assert result["inventory"] == {
        "stock_store": 5,
        "stock_supplier": 10,
        "availability": "In Stock",
    }


def test_prepare_all_records_inventory_update(
    mock_dependencies: dict[str, MagicMock],
) -> None:
    # Setup mocks
    mock_dependencies["get_store_id"].return_value = 1
    mock_dependencies["get_brand_id"].return_value = 10

    # Pricing same, Inventory different
    mock_dependencies["prepare_pricing"].return_value = {"price": 100.0}
    mock_dependencies["prepare_inventory"].return_value = {
        "stock_store": 0,
        "stock_supplier": 10,
        "availability": "Out of Stock",
    }

    # Inputs
    item: dict[str, Any] = {}
    normalized: dict[str, Any] = {
        "store_name": "Store",
        "brand_name": "Brand",
        "mpn": "MPN1",
        "ean": "EAN1",
        "sku": "SKU1",
    }
    seen_store_ids = {1}
    seen_brand_ids = {10}
    seen_hardware_mpns = {"MPN1"}
    seen_listings = {(1, "SKU1")}

    # Execute
    result = prepare_all_records(
        item,
        normalized,
        seen_store_ids,
        seen_brand_ids,
        seen_hardware_mpns,
        seen_listings,
    )

    # Assertions
    assert result["prices"] == {"price": 100.0}  # Price always returned
    assert result["inventory"]["stock_store"] == 0
    assert result["inventory"]["availability"] == "Out of Stock"
