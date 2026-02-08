import json
import logging
import os
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
        spider.logger = logging.getLogger("test_spider")
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
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Test that missing MPN triggers a warning but continues processing.
        """
        # Ensure the pipeline's crawler has this spider set
        pipeline.crawler.spider = spider
        item = {
            "store": "Azerty",
            "brand": "Corsair",
            "sku": "SKU123",
            "mpn": None,  # Missing MPN
        }

        with caplog.at_level(logging.WARNING, logger="test_spider"):
            pipeline.process_item(item, spider)

        assert "no MPN" in caplog.text

    def test_get_store_id(self, pipeline: SplitToTablesPipeline) -> None:
        """Test the internal helper for resolving store IDs."""
        assert pipeline._get_store_id("Azerty") == 1
        assert pipeline._get_store_id("Alternate") == 2
        assert pipeline._get_store_id("Unknown Store") == 999

    def test_get_brand_id(self, pipeline: SplitToTablesPipeline) -> None:
        """Test the internal helper for resolving brand IDs."""
        id_corsair = pipeline._get_brand_id("Corsair")
        id_gskill = pipeline._get_brand_id("G.Skill")
        id_none = pipeline._get_brand_id(None)

        assert isinstance(id_corsair, int)
        assert id_corsair > 0
        assert id_corsair != id_gskill
        assert id_none == 0

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
        """Test that open_spider does not create directory in prod env."""
        crawler = MagicMock(spec=Crawler)
        crawler.settings = Settings({"RUN_ENV": "prod"})
        crawler.spider = spider
        pipeline = SplitToTablesPipeline(crawler)

        spider.name = "azerty"

        with patch("os.makedirs") as mock_makedirs:
            pipeline.open_spider()
            mock_makedirs.assert_not_called()
            assert pipeline.data_dir == ""

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

        pipeline._write_to_bigquery.assert_called_once()
        pipeline._write_to_local.assert_not_called()

    def test_deduplication_loading(self, pipeline: SplitToTablesPipeline) -> None:
        """Test that existing IDs are loaded to prevent duplicates."""
        pipeline.data_dir = "tests/data_mock"
        os.makedirs(pipeline.data_dir, exist_ok=True)

        # Create dummy store file
        with open(os.path.join(pipeline.data_dir, "stores.jsonl"), "w") as f:
            f.write(json.dumps({"store_id": 1, "store_name": "TestStore"}) + "\n")

        # Create dummy brand file
        with open(os.path.join(pipeline.data_dir, "brands.jsonl"), "w") as f:
            f.write(json.dumps({"brand_id": 100, "brand_name": "TestBrand"}) + "\n")

        pipeline._load_seen_ids()

        assert 1 in pipeline.seen_store_ids
        assert 100 in pipeline.seen_brand_ids

        # Cleanup
        import shutil

        shutil.rmtree(pipeline.data_dir)
