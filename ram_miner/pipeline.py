import json
import os
from typing import Any

import scrapy
from google.cloud import bigquery
from scrapy.crawler import Crawler

import ram_miner.state as state
from ram_miner.utils.cleaning import ensure_timestamp, normalize_identifier
from ram_miner.utils.io import upload_to_gcs
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
        self.table_names = self.crawler.settings.getlist(
            "BIGQUERY_TABLE_NAMES",
        )
        self.merge_keys = self.crawler.settings.get("MERGE_KEYS")

        if self.run_env == "prod":
            self.bucket_name = self.crawler.settings.get("GCS_BUCKET_NAME")
        else:
            self.bucket_name = None

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
            for table in self.table_names:
                local_path = os.path.join(self.data_dir, f"{table}.jsonl")
                if os.path.exists(local_path):
                    spider.logger.info(
                        f"Uploading {table} to GCS bucket {self.bucket_name}"
                    )
                    upload_to_gcs(self.bucket_name, local_path)

            self._write_to_bigquery(spider)

    def _load_state(self) -> None:
        loaded = state.load_state(self.data_dir, self.bucket_name)
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
        Standardizes JSONL files to BigQuery tables using a temporary table approach.
        1. Loads data into temp tables.
        2. Merges temp tables into final tables (insert new, update existing if data changed).
        3. Drops temp tables.
        """
        project_id = self.crawler.settings.get("GCP_PROJECT_ID")
        dataset_id = self.crawler.settings.get("GCP_DATASET_ID", "retail_ram_data")

        if not project_id or not dataset_id:
            spider.logger.error("Missing required BigQuery configuration")
            return

        # Initialize BigQuery client
        try:
            client = bigquery.Client(project=project_id)
        except Exception as e:
            spider.logger.error(f"Failed to initialize BigQuery client: {e}")
            return

        # Upload each JSONL file to its corresponding BigQuery table
        for table_name in self.table_names:
            jsonl_file = os.path.join(self.data_dir, f"{table_name}.jsonl")

            if not os.path.exists(jsonl_file) or os.path.getsize(jsonl_file) == 0:
                spider.logger.debug(f"Skipping {table_name}.jsonl (missing or empty)")
                continue

            final_table_id = f"{project_id}.{dataset_id}.{table_name}"
            # Use specific temp table name to avoid collisions
            temp_table_id = f"{project_id}.{dataset_id}.temp_{table_name}_{spider.name}"

            try:
                # 1. Load data into temporary table
                self._load_to_temp_table(client, jsonl_file, temp_table_id, spider)

                # 2. Ensure final table exists (create if missing)
                self._ensure_table_exists(client, final_table_id, temp_table_id, spider)

                # 3. Merge temp table into final table
                primary_keys = self.merge_keys.get(table_name, [])
                if not primary_keys:
                    spider.logger.warning(
                        f"No merge keys defined for {table_name}, skipping merge."
                    )
                    # Still clean up temp table
                    client.delete_table(temp_table_id, not_found_ok=True)
                    continue

                self._merge_tables(
                    client, temp_table_id, final_table_id, primary_keys, spider
                )

                # 4. Clean up temp table
                client.delete_table(temp_table_id, not_found_ok=True)

            except Exception as e:
                spider.logger.error(f"Failed to load {table_name} to BigQuery: {e}")

    def _load_to_temp_table(
        self,
        client: bigquery.Client,
        jsonl_file: str,
        temp_table_id: str,
        spider: scrapy.Spider,
    ) -> None:
        """Loads JSONL data into a temporary BigQuery table."""
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True,
            create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        )

        with open(jsonl_file, "rb") as source_file:
            load_job = client.load_table_from_file(
                source_file, temp_table_id, job_config=job_config
            )
        load_job.result()
        spider.logger.info(
            f"Loaded {load_job.output_rows} rows into temp table {temp_table_id}"
        )

    def _ensure_table_exists(
        self,
        client: bigquery.Client,
        final_table_id: str,
        temp_table_id: str,
        spider: scrapy.Spider,
    ) -> None:
        """Creates the final table using the temp table's schema if it doesn't exist."""
        try:
            client.get_table(final_table_id)
        except Exception:
            spider.logger.info(f"Table {final_table_id} not found, creating it...")
            temp_table = client.get_table(temp_table_id)
            final_table = bigquery.Table(final_table_id, schema=temp_table.schema)
            # Use partitioning/clustering if needed, for now just simple schema copy
            client.create_table(final_table)
            spider.logger.info(f"Created table {final_table_id}")

    def _build_merge_query(
        self,
        final_table_id: str,
        temp_table_id: str,
        primary_keys: list[str],
        schema: list[Any],
    ) -> str:
        """Constructs the MERGE query for upserting data."""
        columns = [field.name for field in schema if field.name not in primary_keys]

        on_clause = " AND ".join([f"T.{key} = S.{key}" for key in primary_keys])

        # Build UPDATE SET clause (COALESCE preserves existing values if source is NULL)
        update_clause = ", ".join(
            [f"{col} = COALESCE(S.{col}, T.{col})" for col in columns]
        )

        all_columns = [field.name for field in schema]
        insert_cols = ", ".join(all_columns)
        insert_vals = ", ".join([f"S.{col}" for col in all_columns])

        if not columns:
            # If only primary keys exist, just insert if missing
            return f"""
                MERGE `{final_table_id}` T
                USING `{temp_table_id}` S
                ON {on_clause}
                WHEN NOT MATCHED THEN
                    INSERT ({insert_cols}) VALUES ({insert_vals})
            """

        return f"""
            MERGE `{final_table_id}` T
            USING `{temp_table_id}` S
            ON {on_clause}
            WHEN MATCHED THEN
                UPDATE SET {update_clause}
            WHEN NOT MATCHED THEN
                INSERT ({insert_cols}) VALUES ({insert_vals})
        """

    def _merge_tables(
        self,
        client: bigquery.Client,
        temp_table_id: str,
        final_table_id: str,
        primary_keys: list[str],
        spider: scrapy.Spider,
    ) -> None:
        """Executes the merge from temporary table to final table."""
        table_ref = client.get_table(temp_table_id)
        merge_query = self._build_merge_query(
            final_table_id, temp_table_id, primary_keys, table_ref.schema
        )

        spider.logger.info(f"Merging {temp_table_id} into {final_table_id}...")
        client.query(merge_query).result()
        spider.logger.info(f"Merge completed for {final_table_id}")
