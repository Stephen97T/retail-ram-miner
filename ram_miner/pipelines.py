from typing import Any

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from ram_miner.utils.cleaning import parse_modules


class RamMinerPipeline:
    def process_item(self, item: Any, spider):
        """Cleans and validates RamItem fields using the adapter consistently."""
        adapter = ItemAdapter(item)

        # 1. Normalize modules (using adapter for all reads/writes)
        modules_raw = adapter.get("modules")
        has_counts = adapter.get("modules_count") is not None
        has_capacity = adapter.get("module_capacity_gb") is not None

        if modules_raw and (not has_counts or not has_capacity):
            count, per_module = parse_modules(modules_raw)
            if count is not None:
                adapter["modules_count"] = count
            if per_module is not None:
                adapter["module_capacity_gb"] = per_module

        # 2. Derived metric: price per GB
        try:
            # Always use adapter.get() to avoid KeyErrors on missing fields
            capacity = adapter.get("capacity_gb")
            price = adapter.get("price")

            if capacity and price and float(capacity) > 0:
                adapter["price_per_gb"] = round(float(price) / float(capacity), 4)
        except (ValueError, TypeError):
            # Log warning if data is present but malformed
            spider.logger.warning(f"Failed price_per_gb calc for {adapter.get('name')}")

        # 3. Validation: Drop items with no price
        if not adapter.get("price"):
            raise DropItem(f"Dropped item with no price: {adapter.get('name')}")

        return item
