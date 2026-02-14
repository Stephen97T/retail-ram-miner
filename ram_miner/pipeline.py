import json
import os
from typing import Any

import scrapy
from scrapy.crawler import Crawler

import ram_miner.state as state
from ram_miner.utils.cleaning import ensure_timestamp, normalize_identifier
from ram_miner.utils.extract import get_brand_id, get_store_id
from ram_miner.utils.records import prepare_all_records


class SplitToTablesPipeline:
    def __init__(self, crawler: Crawler) -> None:
        self.crawler = crawler
        self.run_env = crawler.settings.get("RUN_ENV", "dev")
        self.data_dir = ""
        self.seen_store_ids: set[int] = set()
        self.seen_brand_ids: set[int] = set()
        self.seen_hardware_mpns: set[str] = set()
        self.seen_listings: set[tuple[int, str]] = set()
        self.latest_prices: dict[tuple[int, str], float | None] = {}
        self.latest_inventory: dict[tuple[int, str], tuple[Any, ...]] = {}

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "SplitToTablesPipeline":
        return cls(crawler)

    def open_spider(self, *args: Any, **kwargs: Any) -> None:
        spider = self.crawler.spider
        if not spider and args:
            spider = args[0]
        if not spider:
            return
        if self.run_env != "prod":
            self.data_dir = os.path.join("data", spider.name)
            os.makedirs(self.data_dir, exist_ok=True)
            self._load_state()

    def _load_state(self) -> None:
        loaded = state.load_state(
            self.data_dir, self.crawler.spider.logger if self.crawler.spider else None
        )
        self.seen_store_ids = loaded["seen_store_ids"]
        self.seen_brand_ids = loaded["seen_brand_ids"]
        self.seen_hardware_mpns = loaded["seen_hardware_mpns"]
        self.seen_listings = loaded["seen_listings"]
        self.latest_prices = loaded["latest_prices"]
        self.latest_inventory = loaded["latest_inventory"]

    def process_item(
        self, item: dict[str, Any], *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        spider = self.crawler.spider
        if not spider and args:
            spider = args[0]
        if not spider:
            raise ValueError("Spider is required for process_item")
        ensure_timestamp(item)
        normalized = self._normalize_item(item)
        records = self._prepare_records(item, normalized, spider)
        if self.run_env == "prod":
            self._write_to_bigquery(records, spider)
        else:
            self._write_to_local(records, spider)
        return item

    def _normalize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        mpn = normalize_identifier(item.get("mpn"))
        if not mpn:
            spider = self.crawler.spider
            if spider and hasattr(spider, "logger"):
                spider.logger.warning(
                    f"Item {item.get('sku')} from {item.get('store')} has no MPN. Hardware specs cannot be consolidated."
                )
        return {
            "mpn": mpn,
            "ean": normalize_identifier(item.get("ean")),
            "store_name": item.get("store", "Unknown"),
            "brand_name": item.get("brand", "Unknown"),
            "sku": str(item.get("sku")),
        }

    def _prepare_records(
        self, item: dict[str, Any], normalized: dict[str, Any], spider: scrapy.Spider
    ) -> dict[str, dict[str, Any]]:
        return prepare_all_records(
            item,
            normalized,
            self.seen_store_ids,
            self.seen_brand_ids,
            self.seen_hardware_mpns,
            self.seen_listings,
            self.latest_prices,
            self.latest_inventory,
            get_store_id,
            get_brand_id,
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
