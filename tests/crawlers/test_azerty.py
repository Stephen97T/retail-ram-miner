import os
from pathlib import Path

import pytest
from scrapy.http import Request, TextResponse

from ram_miner.items import RamItem
from ram_miner.spiders.crawlers.azerty import AzertySpider


def fake_response_from_file(file_name: str, url: str) -> TextResponse:
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
    def spider(self) -> AzertySpider:
        return AzertySpider()

    def test_parse_product_links(self, spider: AzertySpider) -> None:
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

    def test_parse_pagination(self, spider: AzertySpider) -> None:
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

    def test_parse_product(self, spider: AzertySpider) -> None:
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

        expected_values = {
            "store": "Azerty",
            "name": "Corsair Vengeance RGB - Geheugen",
            "url": "https://azerty.nl/product/corsair-vengeance-rgb-geheugen/9509576",
            "currency": "EUR",
            "price": 449.0,
            "price_per_gb": 14.0312,
            "sku": "9509576",
            "mpn": "CMH32GX5M2F6000Z36",
            "ean": "0840440419396",
            "brand": "CORSAIR",
            "capacity_gb": 32,
            "clock_speed": 3000,
            "transfer_speed": 6000,
            "generation": "DDR5",
            "latency": 36,
            "modules": "2 x 16",
            "modules_count": 2,
            "module_capacity_gb": 16,
            "system_of_usage": "desktop",
            "availability": "In Stock",
            "stock_quantity": 77,
            "stock_supplier": None,
            "order_limit": 1,
            "image_url": "https://azerty.nl/media/catalog/product/K/n/Knipsel.jpg?quality=80&bg-color=255,255,255&fit=bounds&height=265&width=265&canvas=265:265",
        }

        for key, expected_value in expected_values.items():
            assert item.get(key) == expected_value, f"Mismatch for field '{key}'"

        assert item.get("timestamp") is not None
