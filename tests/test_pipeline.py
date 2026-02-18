import os
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest
from scrapy.crawler import Crawler
from scrapy.settings import Settings

from ram_miner.pipeline import SplitToTablesPipeline


class TestSplitToTablesPipeline:
    @pytest.fixture
    def pipeline(self) -> SplitToTablesPipeline:
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "test"})
        # Spider needed for logs in some cases
        crawler.spider = MagicMock()
        return SplitToTablesPipeline(crawler)

    @pytest.fixture
    def spider(self) -> MagicMock:
        spider = MagicMock()
        spider.logger = MagicMock()  # Mock logger for assertions
        spider.name = "test_spider"
        return spider

    def test_process_item_basic_flow(
        self, pipeline: SplitToTablesPipeline, spider: MagicMock
    ) -> None:
        """
        Test that process_item runs without error and adds timestamps/normalization.
        """
        # Ensure the pipeline's crawler has this spider set
        pipeline.crawler.spider = spider

        item = {
            "store": "Azerty",
            "brand": "Corsair",
            "sku": "SKU123",
            "mpn": "CMH32GX5M2F6000Z36",
            "ean": "0840440419396",
            "price": 100.0,
            "availability": "In Stock",
        }

        # Run pipeline
        processed_item = pipeline.process_item(item, spider)

        # 1. Assert input item is returned
        assert processed_item == item

        # 2. Assert timestamp was added
        assert processed_item.get("timestamp") is not None

        # 3. Validation - since DB code is commented out, we can't assert on DB calls.
        # But we can check if it resolved store IDs internally if we exposed that, or just rely on no exception.

    def test_process_item_missing_mpn(
        self,
        pipeline: SplitToTablesPipeline,
        spider: MagicMock,
    ) -> None:
        """
        Test that missing MPN triggers a warning but continues processing.
        """
        # Ensure the pipeline's crawler has this spider set
        pipeline.crawler.spider = spider
        pipeline.data_dir = "test_data"  # Set data_dir to avoid warning
        # Mock write methods to prevent actual file operations
        pipeline._write_to_local = MagicMock()  # type: ignore[method-assign]

        item = {
            "store": "Azerty",
            "brand": "Corsair",
            "sku": "SKU123",
            "mpn": None,  # Missing MPN
        }

        pipeline.process_item(item, spider)

        # Check that warning was logged
        spider.logger.warning.assert_called()
        call_args = str(spider.logger.warning.call_args)
        assert "no MPN" in call_args

    def test_get_store_id(self, pipeline: SplitToTablesPipeline) -> None:
        pass

    def test_get_brand_id(self, pipeline: SplitToTablesPipeline) -> None:
        pass

    def test_from_crawler(self) -> None:
        """Test that pipeline is initialized from crawler settings."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "prod"})

        pipeline = SplitToTablesPipeline.from_crawler(crawler)
        assert pipeline.run_env == "prod"
        assert pipeline.crawler == crawler

        crawler.settings = Settings({})
        pipeline = SplitToTablesPipeline.from_crawler(crawler)
        assert pipeline.run_env == "dev"

    def test_open_spider_dev(self, spider: MagicMock) -> None:
        """Test that open_spider creates directory in non-prod env."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "dev"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        spider.name = "azerty"

        with patch("os.makedirs") as mock_makedirs:
            pipeline.open_spider()  # passing spider is deprecated
            expected_path = os.path.join("data", "azerty")
            mock_makedirs.assert_called_once_with(expected_path, exist_ok=True)
            assert pipeline.data_dir == expected_path

            # Since we didn't mock _load_seen_ids, this might fail or run.
            # In test environment, it's safer to patch it or ensure it's safe.
            # In this test, we only patch os.makedirs. load_seen_ids uses exists() which will be false in mock env presumably, or check for real files.
            # However, open now calls _load_seen_ids.

    def test_open_spider_prod(self, spider: MagicMock) -> None:
        """Test that open_spider creates directory even in prod env (for JSONL staging)."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "prod"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        spider.name = "azerty"

        with patch("os.makedirs") as mock_makedirs:
            pipeline.open_spider()
            # Directory is always created (even in prod) for JSONL staging
            expected_path = os.path.join("data", "azerty")
            mock_makedirs.assert_called_once_with(expected_path, exist_ok=True)
            assert pipeline.data_dir == expected_path

    def test_write_to_local(self, spider: MagicMock) -> None:
        """Test writing records to local JSONL files."""
        # Use fixture if possible but need custom settings?
        # Easier to recreate
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "dev"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        pipeline.data_dir = os.path.join("data", "test_spider")

        records = {"stores": {"id": 1, "name": "Azerty"}}

        with patch("builtins.open", mock_open()) as mock_file:
            pipeline._write_to_local(records, spider)

            mock_file.assert_called_once_with(
                os.path.join("data", "test_spider", "stores.jsonl"),
                "a",
                encoding="utf-8",
            )
            handle = mock_file()
            # Verify we wrote a JSON line
            assert '{"id": 1, "name": "Azerty"}\n' in handle.write.call_args[0][0]

    def test_write_to_local_no_dir(self, spider: MagicMock) -> None:
        """Test that write_to_local aborts if data_dir is not set."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "dev"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        pipeline.data_dir = ""  # Not set

        records = {"stores": {"id": 1}}

        with patch("builtins.open", mock_open()) as mock_file:
            pipeline._write_to_local(records, spider)
            mock_file.assert_not_called()

    def test_process_item_dispatch_dev(self, spider: MagicMock) -> None:
        """Test dispatching to local writer in dev env."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "dev"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        # Mocking _write_to_local to verify it's called
        pipeline._write_to_local = MagicMock()  # type: ignore[method-assign]
        pipeline._write_to_bigquery = MagicMock()  # type: ignore[method-assign]

        item = {"store": "Azerty", "brand": "Corsair"}
        pipeline.process_item(item, spider)

        pipeline._write_to_local.assert_called_once()
        pipeline._write_to_bigquery.assert_not_called()

    def test_process_item_dispatch_prod(self, spider: MagicMock) -> None:
        """Test dispatching to bigquery writer in prod env."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "prod"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        # Mocking writers
        pipeline._write_to_local = MagicMock()  # type: ignore[method-assign]
        pipeline._write_to_bigquery = MagicMock()  # type: ignore[method-assign]

        item = {"store": "Azerty", "brand": "Corsair"}
        pipeline.process_item(item, spider)

        # In prod, we still write to local first, bigquery is done on close
        pipeline._write_to_local.assert_called_once()
        pipeline._write_to_bigquery.assert_not_called()

    def test_close_spider_prod(self, spider: MagicMock) -> None:
        """Test close_spider triggers bigquery upload in prod."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "prod"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)
        pipeline._write_to_bigquery = MagicMock()  # type: ignore[method-assign]

        pipeline.close_spider(spider)
        pipeline._write_to_bigquery.assert_called_once_with(spider)

    def test_close_spider_dev(self, spider: MagicMock) -> None:
        """Test close_spider does NOT trigger bigquery upload in dev."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "dev"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)
        pipeline._write_to_bigquery = MagicMock()  # type: ignore[method-assign]

        pipeline.close_spider(spider)
        pipeline._write_to_bigquery.assert_not_called()

    @patch("ram_miner.state._read_lines")
    def test_deduplication_loading(
        self, mock_read_lines: MagicMock, pipeline: SplitToTablesPipeline
    ) -> None:
        """Test that existing IDs are loaded to prevent duplicates."""
        pipeline.data_dir = "tests/data_mock"

        # Define side effects for read_lines based on filepath
        def read_lines_side_effect(
            file_path: str, bucket_name: str | None = None
        ) -> list[dict[str, Any] | None]:
            filename = os.path.basename(file_path)
            if filename == "stores.jsonl":
                return [{"store_id": 1, "store_name": "TestStore"}]
            elif filename == "brands.jsonl":
                return [{"brand_id": 100, "brand_name": "TestBrand"}]
            elif filename == "hardware.jsonl":
                return [{"mpn": "MPN1"}]
            elif filename == "listings.jsonl":
                return [{"store_id": 1, "store_sku": "SKU1"}]
            return []

        mock_read_lines.side_effect = read_lines_side_effect

        pipeline._load_state()

        assert 1 in pipeline.seen_store_ids
        assert 100 in pipeline.seen_brand_ids
        assert "MPN1" in pipeline.seen_hardware_mpns
        assert (1, "SKU1") in pipeline.seen_listings

    @patch("ram_miner.pipeline.bigquery")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("builtins.open", new_callable=mock_open, read_data=b'{"test": "data"}')
    def test_write_to_bigquery_success(
        self,
        mock_file: MagicMock,
        mock_getsize: MagicMock,
        mock_exists: MagicMock,
        mock_bigquery: MagicMock,
        spider: MagicMock,
    ) -> None:
        """Test successful BigQuery upload with merge strategy."""
        # Setup
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings(
            {
                "RUN_ENV": "prod",
                "GCP_PROJECT_ID": "test-project",
                "GCP_DATASET_ID": "test_dataset",
                "BIGQUERY_TABLE_NAMES": ["stores", "brands"],
                "MERGE_KEYS": {"stores": ["store_id"], "brands": ["brand_id"]},
            }
        )
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)
        pipeline.data_dir = "data/test_spider"

        # Mock file system
        mock_exists.return_value = True
        mock_getsize.return_value = 100  # Non-empty file

        # Mock BigQuery client and jobs
        mock_client = MagicMock()
        mock_bigquery.Client.return_value = mock_client

        # Mock Load Job
        mock_load_job = MagicMock()
        mock_load_job.output_rows = 5
        mock_client.load_table_from_file.return_value = mock_load_job

        # Mock Table Schema for Merge
        mock_table = MagicMock()
        mock_field = MagicMock()
        mock_field.name = "test_col"
        mock_table.schema = [mock_field]
        mock_client.get_table.return_value = mock_table

        # Mock Query Job (Merge)
        mock_query_job = MagicMock()
        mock_client.query.return_value = mock_query_job

        # Execute
        pipeline._write_to_bigquery(spider)

        # Assertions
        mock_bigquery.Client.assert_called_with(project="test-project")

        # Verify Load Job calls (2 tables)
        assert mock_client.load_table_from_file.call_count == 2
        mock_load_job.result.assert_called()

        # Verify Merge Query calls (2 tables)
        assert mock_client.query.call_count == 2
        mock_query_job.result.assert_called()

        # Verify Temp Table Cleanup (2 tables)
        assert mock_client.delete_table.call_count == 2

    @patch("ram_miner.pipeline.bigquery")
    def test_write_to_bigquery_missing_project_id(
        self, mock_bigquery: MagicMock, spider: MagicMock
    ) -> None:
        """Test that missing GCP_PROJECT_ID is handled gracefully."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "prod"})  # No GCP_PROJECT_ID
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        pipeline._write_to_bigquery(spider)

        # Should not attempt to create client
        mock_bigquery.Client.assert_not_called()

    @patch("ram_miner.pipeline.bigquery")
    def test_write_to_bigquery_client_initialization_error(
        self, mock_bigquery: MagicMock, spider: MagicMock
    ) -> None:
        """Test handling of BigQuery client initialization errors."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings(
            {"RUN_ENV": "prod", "GCP_PROJECT_ID": "test-project"}
        )
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        # Mock client initialization to raise an error
        mock_bigquery.Client.side_effect = Exception("Authentication failed")

        pipeline._write_to_bigquery(spider)

        # Should log error
        spider.logger.error.assert_called_with(
            "Failed to initialize BigQuery client: Authentication failed"
        )

    @patch("ram_miner.pipeline.bigquery")
    @patch("os.path.exists")
    def test_write_to_bigquery_missing_file(
        self, mock_exists: MagicMock, mock_bigquery: MagicMock, spider: MagicMock
    ) -> None:
        """Test that missing JSONL files are skipped."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings(
            {
                "RUN_ENV": "prod",
                "GCP_PROJECT_ID": "test-project",
                "BIGQUERY_TABLE_NAMES": ["stores"],
            }
        )
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)
        pipeline.data_dir = "data/test_spider"

        # Mock file doesn't exist
        mock_exists.return_value = False

        mock_client = MagicMock()
        mock_bigquery.Client.return_value = mock_client

        pipeline._write_to_bigquery(spider)

        # Should not attempt to load
        mock_client.load_table_from_file.assert_not_called()
        spider.logger.debug.assert_called_with(
            "Skipping stores.jsonl (missing or empty)"
        )

    @patch("ram_miner.pipeline.bigquery")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_write_to_bigquery_empty_file(
        self,
        mock_getsize: MagicMock,
        mock_exists: MagicMock,
        mock_bigquery: MagicMock,
        spider: MagicMock,
    ) -> None:
        """Test that empty JSONL files are skipped."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings(
            {
                "RUN_ENV": "prod",
                "GCP_PROJECT_ID": "test-project",
                "BIGQUERY_TABLE_NAMES": ["stores"],
            }
        )
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)
        pipeline.data_dir = "data/test_spider"

        # Mock file exists but is empty
        mock_exists.return_value = True
        mock_getsize.return_value = 0

        mock_client = MagicMock()
        mock_bigquery.Client.return_value = mock_client

        pipeline._write_to_bigquery(spider)

        # Should not attempt to load
        mock_client.load_table_from_file.assert_not_called()
        spider.logger.debug.assert_called_with(
            "Skipping stores.jsonl (missing or empty)"
        )

    @patch("ram_miner.pipeline.bigquery")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("builtins.open", new_callable=mock_open, read_data=b'{"test": "data"}')
    def test_write_to_bigquery_load_error(
        self,
        mock_file: MagicMock,
        mock_getsize: MagicMock,
        mock_exists: MagicMock,
        mock_bigquery: MagicMock,
        spider: MagicMock,
    ) -> None:
        """Test handling of errors during BigQuery load."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings(
            {
                "RUN_ENV": "prod",
                "GCP_PROJECT_ID": "test-project",
                "BIGQUERY_TABLE_NAMES": ["stores"],
            }
        )
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)
        pipeline.data_dir = "data/test_spider"

        # Mock file system
        mock_exists.return_value = True
        mock_getsize.return_value = 100

        # Mock BigQuery client to raise error during load
        mock_client = MagicMock()
        mock_bigquery.Client.return_value = mock_client
        mock_client.load_table_from_file.side_effect = Exception("Schema mismatch")

        pipeline._write_to_bigquery(spider)

        # Should log error
        spider.logger.error.assert_called_with(
            "Failed to load stores to BigQuery: Schema mismatch"
        )

    @patch("ram_miner.pipeline.bigquery")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("builtins.open", new_callable=mock_open, read_data=b'{"test": "data"}')
    def test_write_to_bigquery_multiple_tables(
        self,
        mock_file: MagicMock,
        mock_getsize: MagicMock,
        mock_exists: MagicMock,
        mock_bigquery: MagicMock,
        spider: MagicMock,
    ) -> None:
        """Test uploading multiple tables to BigQuery."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings(
            {
                "RUN_ENV": "prod",
                "GCP_PROJECT_ID": "test-project",
                "GCP_DATASET_ID": "test_dataset",
                "BIGQUERY_TABLE_NAMES": ["stores", "brands", "hardware"],
                "MERGE_KEYS": {
                    "stores": ["store_id"],
                    "brands": ["brand_id"],
                    "hardware": ["mpn"],
                },
            }
        )
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)
        pipeline.data_dir = "data/test_spider"

        # Mock file system
        mock_exists.return_value = True
        mock_getsize.return_value = 100

        # Mock BigQuery client
        mock_client = MagicMock()
        mock_bigquery.Client.return_value = mock_client
        mock_load_job = MagicMock()
        mock_load_job.output_rows = 10
        mock_client.load_table_from_file.return_value = mock_load_job

        # Mock for merge
        mock_table = MagicMock()
        mock_table.schema = []  # No extra cols
        mock_client.get_table.return_value = mock_table
        mock_client.query.return_value = MagicMock()

        pipeline._write_to_bigquery(spider)

        # Should call load_table, query, delete for 3 times
        assert mock_client.load_table_from_file.call_count == 3
        # assert mock_load_job.result.call_count == 3 # result called on same mock execution 3 times
        assert mock_client.query.call_count == 3
        assert mock_client.delete_table.call_count == 3

    @patch("ram_miner.pipeline.bigquery")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("builtins.open", new_callable=mock_open, read_data=b'{"test": "data"}')
    def test_write_to_bigquery_job_config(
        self,
        mock_file: MagicMock,
        mock_getsize: MagicMock,
        mock_exists: MagicMock,
        mock_bigquery: MagicMock,
        spider: MagicMock,
    ) -> None:
        """Test that BigQuery job config is set correctly."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings(
            {
                "RUN_ENV": "prod",
                "GCP_PROJECT_ID": "test-project",
                "BIGQUERY_TABLE_NAMES": ["stores"],
            }
        )
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)
        pipeline.data_dir = "data/test_spider"

        # Mock file system
        mock_exists.return_value = True
        mock_getsize.return_value = 100

        # Mock BigQuery components
        mock_client = MagicMock()
        mock_bigquery.Client.return_value = mock_client
        mock_load_job = MagicMock()
        mock_load_job.output_rows = 5
        mock_client.load_table_from_file.return_value = mock_load_job

        # Mock merge parts so it doesn't crash
        mock_client.get_table.return_value = MagicMock(schema=[])
        mock_client.query.return_value = MagicMock()

        pipeline._write_to_bigquery(spider)

        # Verify LoadJobConfig was created with correct parameters
        mock_bigquery.LoadJobConfig.assert_called()
        call_kwargs = mock_bigquery.LoadJobConfig.call_args.kwargs
        assert (
            call_kwargs["source_format"]
            == mock_bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        )
        assert (
            call_kwargs["write_disposition"]
            == mock_bigquery.WriteDisposition.WRITE_TRUNCATE
        )
        assert call_kwargs["autodetect"] is True
