from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

import scrapy
from scrapy.http import Response

from ram_miner.items import RamItem
from ram_miner.utils.extract import extract_int


class AzertySpider(scrapy.Spider):
    name = "azerty"
    allowed_domains = ["azerty.nl"]
    start_urls = ["https://azerty.nl/componenten/geheugen"]

    def parse(self, response: Response) -> Generator[scrapy.Request, None, None]:
        """
        Parse listing pages used to discover RAM products.
        """
        # 1. Product Links
        product_links = response.css(
            ".product_list_item a.product_name::attr(href)"
        ).getall()
        # Fallback broad selector if specific class unknown (adjust scope as needed)
        if not product_links:
            # Often product cards have headers or specific wrappers
            product_links = response.css("div.product-card a::attr(href)").getall()

        for link in product_links:
            yield response.follow(link, callback=self.parse_product)

        # 2. Pagination
        # Locate 'next' button or page numbers
        next_page = (
            response.css("a.next::attr(href)").get()
            or response.css("li.next a::attr(href)").get()
        )
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_product(self, response: Response) -> Generator[RamItem, None, None]:
        """
        Parse individual RAM product page for specs and pricing.
        """
        item = RamItem()

        # --- Metadata ---
        item["store"] = "Azerty"
        item["url"] = response.url
        item["timestamp"] = datetime.now()
        item["currency"] = "EUR"

        # --- Basic Product Info ---
        item["name"] = response.css("h1::text").get(default="").strip()
        item["sku"] = response.css(".sku::text").get()  # Often near title
        item["image_url"] = response.css(".product-image img::attr(src)").get()

        # --- Pricing ---
        # Price text usually formatted like "€ 120,95" or "120,95"
        price_raw = response.css(".current-price::text").get()
        if price_raw:
            clean_price = (
                price_raw.replace("\u20ac", "")  # Remove Euro symbol
                .replace("€", "")
                .replace(".", "")  # Remove thousands separator (EU format)
                .replace(",", ".")  # Convert decimal separator
                .strip()
            )
            try:
                item["price"] = float(clean_price)
            except ValueError:
                self.logger.warning(
                    f"Failed to parse price: {price_raw} at {response.url}"
                )

        # --- Availability ---
        stock_text = response.css(".stock-status::text").get()
        item["availability"] = (
            "In Stock"
            if stock_text and "op voorraad" in stock_text.lower()
            else "Out of Stock"
        )

        # --- Technical Specs ---
        # Specs are often in a <table> or <dl> list. We iterate rows to find keys.
        # Example structure: <tr><th>Speed</th><td>6000 MHz</td></tr>
        specs_table = response.css("table.attributes tr, dl.spec-list div")

        for row in specs_table:
            # Extract key/value pair (adjust selectors for th/td or dt/dd)
            key = row.css("th::text, dt::text").get(default="").strip().lower()
            val = row.css("td::text, dd::text").get(default="").strip()

            if not key or not val:
                continue

            # Map site-specific spec labels to our Item fields
            if "capaciteit" in key or "capacity" in key:
                # e.g., "32 GB" -> 32
                item["capacity_gb"] = extract_int(val)
            elif "snelheid" in key or "speed" in key:
                # e.g., "6000 MHz" -> 6000
                item["speed_mhz"] = extract_int(val)
            elif "type" in key or "technologie" in key:
                # e.g., "DDR5"
                item["generation"] = val
            elif "latency" in key or "cas" in key:
                # e.g., "CL30" -> 30
                item["latency"] = extract_int(val)
            elif "modules" in key or "kit" in key:
                # e.g., "2 x 16 GB" (Note: Pipeline will normalize this via 'parse_modules')
                item["modules"] = val
            elif "voltage" in key:
                # Optional: could add voltage field if needed
                pass

        yield item
