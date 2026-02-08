from ram_miner.utils.processing import (
    prepare_brand_record,
    prepare_hardware_record,
    prepare_inventory_record,
    prepare_listing_record,
    prepare_pricing_record,
    prepare_store_record,
)

TEST_ITEM = {
    # --- Hardware & Brand (Static Spec Data) ---
    "brand": "Corsair",
    "mpn": "MPN123",
    "ean": "EAN123",
    "capacity_gb": 32,
    "clock_speed": 6000,
    "transfer_speed": 5600,
    "generation": "DDR5",
    "latency": 36,
    "modules_count": 2,
    "module_capacity_gb": 16,
    "system_of_usage": "desktop",
    # --- Listing Information (Store Specific) ---
    "store": "Azerty",
    "sku": "SKU123",
    "name": "Product Name",
    "url": "http://example.com",
    "image_url": "http://example.com/image.jpg",
    "modules": "2x16GB",
    # --- Pricing Information ---
    "price": 100.0,
    "price_per_gb": 3.125,
    "currency": "EUR",
    # --- Inventory Information ---
    "availability": "In Stock",
    "stock_quantity": 10,
    "stock_supplier": 5,
    "order_limit": 2,
    # --- Metadata ---
    "timestamp": "2023-01-01",
}


def test_prepare_store_record() -> None:
    store_id = 1
    result = prepare_store_record(TEST_ITEM, store_id)
    assert result == {
        "store_id": 1,
        "store_name": "Azerty",
        "timestamp": "2023-01-01",
    }


def test_prepare_brand_record() -> None:
    brand_id = 100
    result = prepare_brand_record(TEST_ITEM, brand_id)
    assert result == {
        "brand_id": 100,
        "brand_name": "Corsair",
    }


def test_prepare_hardware_record() -> None:
    mpn = "MPN123"
    ean = "EAN123"
    brand_id = 100
    result = prepare_hardware_record(TEST_ITEM, mpn, ean, brand_id)
    assert result == {
        "mpn": "MPN123",
        "brand_id": 100,
        "ean": "EAN123",
        "capacity_gb": 32,
        "clock_speed": 6000,
        "transfer_speed": 5600,
        "generation": "DDR5",
        "latency": 36,
        "modules_count": 2,
        "module_capacity_gb": 16,
        "system_of_usage": "desktop",
    }


def test_prepare_listing_record() -> None:
    store_id = 1
    mpn = "MPN123"
    result = prepare_listing_record(TEST_ITEM, store_id, mpn)
    assert result == {
        "store_sku": "SKU123",
        "store_id": 1,
        "mpn": "MPN123",
        "name": "Product Name",
        "url": "http://example.com",
        "image_url": "http://example.com/image.jpg",
        "modules_label": "2x16GB",
        "timestamp": "2023-01-01",
    }


def test_prepare_pricing_record() -> None:
    store_id = 1
    result = prepare_pricing_record(TEST_ITEM, store_id)
    assert result == {
        "store_sku": "SKU123",
        "store_id": 1,
        "price": 100.0,
        "price_per_gb": 3.125,
        "currency": "EUR",
        "timestamp": "2023-01-01",
    }


def test_prepare_inventory_record() -> None:
    store_id = 1
    result = prepare_inventory_record(TEST_ITEM, store_id)
    assert result == {
        "store_sku": "SKU123",
        "store_id": 1,
        "stock_store": 10,
        "stock_supplier": 5,
        "availability": "In Stock",
        "order_limit": 2,
        "timestamp": "2023-01-01",
    }
