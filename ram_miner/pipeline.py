import json
import os
from datetime import UTC, datetime
from typing import Any

import scrapy
from scrapy.crawler import Crawler

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
    def __init__(self, crawler: Crawler) -> None:
        self.crawler = crawler
        self.run_env = crawler.settings.get("RUN_ENV", "dev")
        self.data_dir = ""
        self.seen_store_ids: set[int] = set()
        self.seen_brand_ids: set[int] = set()

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "SplitToTablesPipeline":
        return cls(crawler)

    def open_spider(self, spider: scrapy.Spider | None = None) -> None:
        # Access spider through crawler since argument is deprecated
        spider = self.crawler.spider or spider
        if not spider:
            # Fallback (should not happen in normal Scrapy execution)
            return

        if self.run_env != "prod":
            self.data_dir = os.path.join("data", spider.name)
            os.makedirs(self.data_dir, exist_ok=True)
            self._load_seen_ids()

    def process_item(
        self, item: dict[str, Any], spider: scrapy.Spider
    ) -> dict[str, Any]:
        # Using spider from crawler is preferred
        current_spider = self.crawler.spider or spider

        ensure_timestamp(item)

        # --- NORMALIZATION STEP ---
        clean_mpn = normalize_identifier(item.get("mpn"))
        clean_ean = normalize_identifier(item.get("ean"))

        if not clean_mpn:
            current_spider.logger.warning(
                f"Item {item.get('sku')} from {item.get('store')} has no MPN. Hardware specs cannot be consolidated."
            )

        # 1. Store Data
        store_name = item.get("store", "Unknown")
        store_id = self._get_store_id(store_name)
        if store_id not in self.seen_store_ids:
            store_record = prepare_store_record(item, store_id)
            store_record["timestamp"] = datetime.now(UTC).isoformat()
            self.seen_store_ids.add(store_id)
        else:
            store_record = {}

        # 2. Brand Data
        brand_name = item.get("brand", "Unknown")
        brand_id = self._get_brand_id(brand_name)
        if brand_id not in self.seen_brand_ids:
            brand_record = prepare_brand_record(item, brand_id)
            brand_record["timestamp"] = datetime.now(UTC).isoformat()
            self.seen_brand_ids.add(brand_id)
        else:
            brand_record = {}

        # 3. Hardware Specs
        hardware_record = prepare_hardware_record(item, clean_mpn, clean_ean, brand_id)

        # 4. Store Listing
        listing_record = prepare_listing_record(item, store_id, clean_mpn)

        # 5. Pricing Data
        pricing_record = prepare_pricing_record(item, store_id)

        # 6. Inventory Data
        inventory_record = prepare_inventory_record(item, store_id)

        # Dispatch based on environment
        records = {
            "stores": store_record,
            "brands": brand_record,
            "hardware": hardware_record,
            "listings": listing_record,
            "prices": pricing_record,
            "inventory": inventory_record,
        }

        if self.run_env == "prod":
            self._write_to_bigquery(records, current_spider)
        else:
            self._write_to_local(records, current_spider)

        return item

    def _load_seen_ids(self) -> None:
        """Loads existing IDs from local files to prevent duplicates across runs."""
        # Load Stores
        store_file = os.path.join(self.data_dir, "stores.jsonl")
        if os.path.exists(store_file):
            try:
                with open(store_file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        if "store_id" in record:
                            self.seen_store_ids.add(record["store_id"])
            except Exception as e:
                if self.crawler.spider:
                    self.crawler.spider.logger.warning(
                        f"Failed to load existing stores: {e}"
                    )

        # Load Brands
        brand_file = os.path.join(self.data_dir, "brands.jsonl")
        if os.path.exists(brand_file):
            try:
                with open(brand_file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        if "brand_id" in record:
                            self.seen_brand_ids.add(record["brand_id"])
            except Exception as e:
                if self.crawler.spider:
                    self.crawler.spider.logger.warning(
                        f"Failed to load existing brands: {e}"
                    )

    def _write_to_local(
        self, records: dict[str, dict[str, Any]], spider: scrapy.Spider
    ) -> None:
        """Writes records to local JSONL files in the data directory."""
        # Safety check to prevent writing to root if directory setup failed
        if not self.data_dir:
            spider.logger.warning("Data directory not set. Skipping local write.")
            return

        for table_name, record in records.items():
            if not record:
                continue

            file_path = os.path.join(self.data_dir, f"{table_name}.jsonl")
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, default=str) + "\n")
            except Exception as e:
                spider.logger.error(f"Failed to write to {table_name}.jsonl: {e}")

    def _write_to_bigquery(
        self, records: dict[str, dict[str, Any]], spider: scrapy.Spider
    ) -> None:
        """
        Placeholder for Google BigQuery insertion.
        Requires 'google-cloud-bigquery' package and credentials.
        """
        spider.logger.info(
            f"Prod mode: Would insert {list(records.keys())} into BigQuery."
        )
        # Example implementation:
        # client = bigquery.Client()
        # for table_id, row in records.items():
        #     table_ref = client.dataset("your_dataset").table(table_id)
        #     errors = client.insert_rows_json(table_ref, [row])
        #     if errors:
        #         spider.logger.error(f"BQ Errors: {errors}")

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
