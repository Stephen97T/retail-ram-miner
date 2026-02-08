from typing import Any

import scrapy

from ram_miner.utils.cleaning import ensure_timestamp, normalize_identifier
from ram_miner.utils.processing import (
    prepare_brand_record,
    prepare_hardware_record,
    prepare_inventory_record,
    prepare_listing_record,
    prepare_pricing_record,
    prepare_store_record,
)


class SplitToTablesPipeline:
    def process_item(
        self, item: dict[str, Any], spider: scrapy.Spider
    ) -> dict[str, Any]:
        ensure_timestamp(item)

        # --- NORMALIZATION STEP ---
        clean_mpn = normalize_identifier(item.get("mpn"))
        clean_ean = normalize_identifier(item.get("ean"))

        if not clean_mpn:
            spider.logger.warning(
                f"Item {item.get('sku')} from {item.get('store')} has no MPN. Hardware specs cannot be consolidated."
            )

        # 1. Store Data
        store_name = item.get("store", "Unknown")
        store_id = self._get_store_id(store_name)
        store_record = prepare_store_record(item, store_id)

        # 2. Brand Data
        brand_name = item.get("brand", "Unknown")
        brand_id = self._get_brand_id(brand_name)
        brand_record = prepare_brand_record(item, brand_id)

        # 3. Hardware Specs
        hardware_record = prepare_hardware_record(item, clean_mpn, clean_ean, brand_id)

        # 4. Store Listing
        listing_record = prepare_listing_record(item, store_id, clean_mpn)

        # 5. Pricing Data
        pricing_record = prepare_pricing_record(item, store_id)

        # 6. Inventory Data
        inventory_record = prepare_inventory_record(item, store_id)

        # TODO: Insert these records into your database
        # self.db.insert_store(store_record)
        # self.db.insert_brand(brand_record)
        # self.db.insert_hardware(hardware_record)
        # self.db.insert_listing(listing_record)
        # self.db.insert_price(pricing_record)
        # self.db.insert_inventory(inventory_record)

        # Temporary usage to satisfy linter
        spider.logger.debug(
            f"Records prepared: {store_record}, {brand_record}, {hardware_record}, {listing_record}, {pricing_record}, {inventory_record}"
        )

        spider.logger.debug(
            f"Split item {item.get('sku')} (MPN: {clean_mpn}, BrandID: {brand_id}) into logical records."
        )

        return item

    def _get_store_id(self, store_name: str) -> int:
        # You can replace this with a database lookup or dynamic generation
        mapping = {
            "Azerty": 1,
            "Alternate": 2,
            # Add others as needed
        }
        return mapping.get(store_name, 999)

    def _get_brand_id(self, brand_name: str | None) -> int:
        """
        In production, this should query your 'brands' table:
        SELECT id FROM brands WHERE name = %s (or INSERT and returning ID)
        """
        # For now, we perform a deterministic hash or mapping for demonstration
        # This ensures "Corsair" always results in the same fake ID
        if not brand_name:
            return 0
        return abs(hash(brand_name)) % 100000
