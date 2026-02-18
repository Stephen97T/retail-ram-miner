import json
import os
from typing import Any

import scrapy
from google.cloud import bigquery
from scrapy.crawler import Crawler

import ram_miner.state as state
from ram_miner.utils.cleaning import ensure_timestamp, normalize_identifier
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

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "SplitToTablesPipeline":
        return cls(crawler)

    def open_spider(self, *args: Any, **kwargs: Any) -> None:
        spider = self.crawler.spider
        if not spider and args:
            spider = args[0]
        if not spider:
            return
        self.data_dir = os.path.join("data", spider.name)
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_state()

    def close_spider(self, spider: scrapy.Spider) -> None:
        if self.run_env == "prod":
            self._write_to_bigquery(spider)

    def _load_state(self) -> None:
        loaded = state.load_state(self.data_dir)
        self.seen_store_ids = loaded["seen_store_ids"]
        self.seen_brand_ids = loaded["seen_brand_ids"]
        self.seen_hardware_mpns = loaded["seen_hardware_mpns"]
        self.seen_listings = loaded["seen_listings"]

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

    def _write_to_bigquery(self, spider: scrapy.Spider) -> None:
        """
        Bulk insert JSONL files to Google BigQuery.
        Reads from ./data/{spider_name}/*.jsonl and loads into BigQuery tables.
        Requires 'google-cloud-bigquery' package and GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        project_id = self.crawler.settings.get("GCP_PROJECT_ID")
        dataset_id = self.crawler.settings.get("GCP_DATASET_ID", "retail_ram_data")

        for id in [project_id, dataset_id]:
            if not id:
                spider.logger.error(f"Missing required BigQuery configuration: {id}")
                return

        # Initialize BigQuery client
        try:
            client = bigquery.Client(project=project_id)
        except Exception as e:
            spider.logger.error(f"Failed to initialize BigQuery client: {e}")
            return

        # Get table names from settings
        table_names = self.crawler.settings.getlist(
            "BIGQUERY_TABLE_NAMES",
        )

        # Upload each JSONL file to its corresponding BigQuery table
        for table_name in table_names:
            jsonl_file = os.path.join(self.data_dir, f"{table_name}.jsonl")

            if not os.path.exists(jsonl_file):
                spider.logger.debug(f"No {table_name}.jsonl file found, skipping")
                continue

            # Check if file is empty
            if os.path.getsize(jsonl_file) == 0:
                spider.logger.debug(f"{table_name}.jsonl is empty, skipping")
                continue

            table_id = f"{project_id}.{dataset_id}.{table_name}"

            try:
                # Configure the load job
                job_config = bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                    autodetect=True,
                    create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
                )

                # Load data from JSONL file
                with open(jsonl_file, "rb") as source_file:
                    load_job = client.load_table_from_file(
                        source_file, table_id, job_config=job_config
                    )

                # Wait for the job to complete
                load_job.result()

                spider.logger.info(
                    f"Loaded {load_job.output_rows} rows into {table_id}"
                )

            except Exception as e:
                spider.logger.error(f"Failed to load {table_name} to BigQuery: {e}")
