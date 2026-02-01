import os
from pathlib import Path

import pytest
from scrapy.http import Request, TextResponse

from ram_miner.items import RamItem
from ram_miner.spiders.crawlers.azerty import AzertySpider


def fake_response_from_file(file_name, url=None):
    """Create a Scrapy fake HTTP response from a HTML file"""
    current_dir = Path("tests/crawlers/html")
    file_path = os.path.join(current_dir, "azerty", file_name)

    if not os.path.exists(file_path):
        pytest.fail(f"Test file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        file_content = f.read()

    response = TextResponse(
        url=url, request=Request(url=url), body=file_content, encoding="utf-8"
    )
    return response


class TestAzertySpider:
    @pytest.fixture
    def spider(self):
        return AzertySpider()

    def test_parse_product_links(self, spider):
        """Test that the parse method extracts product links correctly."""
        response = fake_response_from_file(
            file_name="product_listing.html",
            url="https://azerty.nl/componenten/geheugen",
        )
        results = list(spider.parse(response))
        requests = [r for r in results if isinstance(r, Request)]

        # Verify we have exactly 24 product requests
        product_requests = [r for r in requests if r.callback == spider.parse_product]
        assert len(product_requests) == 24, (
            f"Expected 24 products, but found {len(product_requests)}"
        )

        # Check the first product URL
        assert (
            product_requests[0].url
            == "https://azerty.nl/product/kingston-fury-beast-black-geheugen/7347764"
        )

    def test_parse_pagination(self, spider):
        """Test that the parse method extracts pagination links correctly."""
        response = fake_response_from_file(
            file_name="product_listing.html",
            url="https://azerty.nl/componenten/geheugen",
        )
        results = list(spider.parse(response))
        requests = [r for r in results if isinstance(r, Request)]

        # Verify we have at least one pagination request (callback=parse)
        pagination_requests = [r for r in requests if r.callback == spider.parse]
        assert len(pagination_requests) > 0, "Next page link was not found"

        # Check the next page URL
        assert (
            pagination_requests[0].url == "https://azerty.nl/componenten/geheugen?p=2"
        )

    def test_parse_product(self, spider):
        """
        Test that parse_product extracts item details correctly.
        """
        response = fake_response_from_file(
            file_name="product_details.html",
            url="https://azerty.nl/product/corsair-vengeance-rgb-geheugen/9509576",
        )
        results = list(spider.parse_product(response, listing_price="449"))

        assert len(results) == 1
        item = results[0]
        assert isinstance(item, RamItem)
        # Assertions for all fields
        assert item["store"] == "Azerty"
        assert item["name"] == "Corsair Vengeance RGB - Geheugen"
        assert (
            item["url"]
            == "https://azerty.nl/product/corsair-vengeance-rgb-geheugen/9509576"
        )
        assert item["currency"] == "EUR"
        assert item["price"] == 449

        # Specs
        assert item["capacity_gb"] == 32
        assert item["speed_mhz"] == 6000  # Should trigger on "Overdrachtssnelheid"
        assert item["generation"] == "DDR5"
        assert item["modules"] == "2 x 16"  # Matches "2 x 16" from table
        assert item["latency"] == 36
        assert item["system_of_usage"] == "PC"

        # Availability - based on file content (I assume it's valid, but let's check field exists)
        assert item.get("availability") in ["In Stock", "Out of Stock"]

        # Metadata
        assert item.get("sku") == "9509576"
        assert (
            item.get("image_url")
            == "https://azerty.nl/media/catalog/product/K/n/Knipsel.jpg?quality=80&bg-color=255,255,255&fit=bounds&height=265&width=265&canvas=265:265"
        )
        assert item.get("timestamp") is not None
