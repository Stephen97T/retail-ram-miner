from typing import Any


def prepare_store_record(item: dict[str, Any], store_id: int) -> dict[str, Any]:
    return {
        "store_id": store_id,
        "store_name": item.get("store", "Unknown"),
    }


def prepare_brand_record(item: dict[str, Any], brand_id: int) -> dict[str, Any]:
    return {
        "brand_id": brand_id,
        "brand_name": item.get("brand", "Unknown"),
    }


def prepare_hardware_record(
    item: dict[str, Any], mpn: str | None, ean: str | None, brand_id: int
) -> dict[str, Any]:
    return {
        "mpn": mpn,
        "brand_id": brand_id,
        "ean": ean,
        "capacity_gb": item.get("capacity_gb"),
        "clock_speed": item.get("clock_speed"),
        "transfer_speed": item.get("transfer_speed"),
        "generation": item.get("generation"),
        "latency": item.get("latency"),
        "modules_count": item.get("modules_count"),
        "module_capacity_gb": item.get("module_capacity_gb"),
        "system_of_usage": item.get("system_of_usage"),
    }


def prepare_listing_record(
    item: dict[str, Any], store_id: int, mpn: str | None
) -> dict[str, Any]:
    return {
        "store_sku": item.get("sku"),
        "store_id": store_id,
        "mpn": mpn,
        "name": item.get("name"),
        "url": item.get("url"),
        "image_url": item.get("image_url"),
        "modules_label": item.get("modules"),
        "timestamp": item.get("timestamp"),
    }


def prepare_pricing_record(item: dict[str, Any], store_id: int) -> dict[str, Any]:
    return {
        "store_sku": item.get("sku"),
        "store_id": store_id,
        "price": item.get("price"),
        "price_per_gb": item.get("price_per_gb"),
        "currency": item.get("currency"),
        "timestamp": item.get("timestamp"),
    }


def prepare_inventory_record(item: dict[str, Any], store_id: int) -> dict[str, Any]:
    return {
        "store_sku": item.get("sku"),
        "store_id": store_id,
        "stock_store": item.get("stock_quantity"),
        "stock_supplier": item.get("stock_supplier"),
        "availability": item.get("availability"),
        "order_limit": item.get("order_limit"),
        "timestamp": item.get("timestamp"),
    }
