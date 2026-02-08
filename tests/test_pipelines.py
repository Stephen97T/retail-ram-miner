import logging
from unittest.mock import MagicMock

import pytest

from ram_miner.pipeline import SplitToTablesPipeline


class TestSplitToTablesPipeline:
    @pytest.fixture
    def pipeline(self) -> SplitToTablesPipeline:
        return SplitToTablesPipeline()

    @pytest.fixture
    def spider(self) -> MagicMock:
        spider = MagicMock()
        spider.logger = logging.getLogger("test_spider")
        return spider

    def test_process_item_basic_flow(
        self, pipeline: SplitToTablesPipeline, spider: MagicMock
    ) -> None:
        """
        Test that process_item runs without error and adds timestamps/normalization.
        """
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
