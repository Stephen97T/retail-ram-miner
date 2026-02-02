from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

import scrapy
from scrapy.http import Response

from ram_miner.items import RamItem
from ram_miner.utils.cleaning import parse_modules
from ram_miner.utils.extract import calculate_price_per_gb, extract_int


class AzertySpider(scrapy.Spider):
    name = "azerty"
    allowed_domains = ["azerty.nl"]
    start_urls = ["https://azerty.nl/componenten/geheugen"]

    def parse(self, response: Response) -> Generator[scrapy.Request, None, None]:
        """
        Parse listing pages used to discover RAM products.
        """
        # 1. Products (URL + Price)
        # We iterate over product cards to capture the price associated with the link.
        # Structure: div.product-info contains both a.product-item-link and span.price
        product_cards = response.css("div.product-info")

        if not product_cards:
            # Fallback if container class differs: just get links
            self.logger.warning(
                "Could not find 'div.product-info', falling back to link extraction."
            )
            product_links = response.css("a.product-item-link::attr(href)").getall()
            if not product_links:
                product_links = set(response.css("div.products a::attr(href)").getall())

            for link in product_links:
                yield response.follow(link, callback=self.parse_product)
        else:
            for card in product_cards:
                url = card.css("a.product-item-link::attr(href)").get()
                price = card.css(".price::text").get()

                if url:
                    yield response.follow(
                        url,
                        callback=self.parse_product,
                        cb_kwargs={"listing_price": price},
                    )

        # 2. Pagination
        # Locate 'next' button or page numbers
        next_page = response.css("a.action.next.btn.btn-secondary::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_product(
        self, response: Response, listing_price: str | None = None
    ) -> Generator[RamItem, None, None]:
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
        # Title is often in h1 > span.base
        item["name"] = (
            response.css("h1 span.base::text").get()
            or response.css("h1::text").get(default="")
        ).strip()

        # SKU Extraction: Try data attribute on form first
        item["sku"] = response.css("form#product_addtocart_form::attr(data-sku)").get()

        # Image Extraction: Try og:image first, then fallback
        item["image_url"] = (
            response.css('meta[property="og:image"]::attr(content)').get()
            or response.css(".product-image img::attr(src)").get()
        )

        # --- Pricing ---
        # Prefer listing price passed from parse(), fallback to detail page price
        price_raw = listing_price
        if not price_raw:
            # Try .current-price (legacy?)
            price_raw = response.css(".current-price::text").get()
        if not price_raw:
            # Try meta itemprop="price"
            price_raw = response.css('meta[itemprop="price"]::attr(content)').get()

        if price_raw:
            clean_price = (
                price_raw.replace("\u20ac", "")  # Remove Euro symbol
                .replace("€", "")
                .replace(".-", "")  # "608.-" -> "608"
                .replace(",-", "")  # "608,-" -> "608"
                .replace(".", "")  # Remove thousands separator (EU format)
                .replace(",", ".")  # Convert decimal separator
                .strip()
            )
            # If price comes from meta (e.g. 484.999461), it might have dots as decimals already
            # The cleaning above removes dots thinking they are thousands separators.
            # We need a check. If it looks like a clean float already, don't break it.
            # Simple heuristic: If it has multiple dots, or comes from meta content (usually dot decimal).

            # Re-evaluating cleaning logic.
            # Meta content: "484.999461" (dot decimal).
            # Listing text: "608,-" (comma decimal, dot thousands).

            # If we used meta, we shouldn't strip dots.
            if 'itemprop="price"' in str(price_raw) or (
                listing_price is None and "meta" in str(response.body)
            ):
                # This detection is weak. Better: try parsing as is first?
                pass

            # Let's write a robust cleaner or just branching logic.
            if listing_price or "current-price" in str(price_raw) or "," in price_raw:
                # Assume Dutch format: 1.000,00
                clean_price = (
                    price_raw.replace("\u20ac", "")
                    .replace("€", "")
                    .replace(".-", "")
                    .replace(",-", "")
                )
                clean_price = clean_price.replace(".", "").replace(",", ".")
            else:
                # Assume standard float format (from meta)
                clean_price = price_raw

            try:
                item["price"] = float(clean_price)
            except ValueError:
                self.logger.warning(
                    f"Failed to parse price: {price_raw} (cleaned: {clean_price}) at {response.url}"
                )

        item["stock_quantity"] = extract_int(
            response.css("span.text-right::text").get()
        )
        # --- Availability ---
        stock_text = response.css(".stock-status::text").get()
        item["availability"] = (
            "In Stock" if item.get("stock_quantity") > 0 else "Out of Stock"
        )

        # Broader selector: "table tr" covers tables without specific class.
        specs_table = response.css("table tr, dl.spec-list div")

        for row in specs_table:
            # Extract key/value pair (adjust selectors for th/td or dt/dd)
            key = row.css("th::text, dt::text").get(default="").strip().lower()
            val = row.css("td::text, dd::text").get(default="").strip()

            if not key or not val:
                continue

            # Map site-specific spec labels to our Item fields
            # Fix: "Intern geheugen" matches "Intern geheugentype", so exclude "type"
            if (
                "capaciteit" in key
                or "capacity" in key
                or ("intern geheugen" in key and "type" not in key)
            ):
                # e.g., "32 GB" -> 32
                item["capacity_gb"] = extract_int(val)
                item["price_per_gb"] = calculate_price_per_gb(
                    item.get("price"), item["capacity_gb"]
                )
            elif "snelheid" in key or "speed" in key or "overdracht" in key:
                # e.g., "6000 MHz" -> 6000
                # Logic to prefer highest value (Transfer Rate vs Clock) if multiple rows exist
                new_speed = extract_int(val)
                current_speed = item.get("speed_mhz", 0)
                if new_speed and new_speed > current_speed:
                    item["speed_mhz"] = new_speed
            elif "geheugentype" in key or "technologie" in key:
                # e.g., "DDR5"
                item["generation"] = val
            elif "latency" in key or "cas" in key:
                # e.g., "CL30" -> 30
                item["latency"] = extract_int(val)
            elif "modules" in key or "kit" in key or "layout" in key:
                # e.g., "2 x 16 GB" (Note: Pipeline will normalize this via 'parse_modules')
                item["modules"] = val
                item["modules_count"], item["module_capacity_gb"] = parse_modules(val)
            elif "component" in key or "gebruik" in key:
                item["system_of_usage"] = val
            elif "voltage" in key:
                # Optional: could add voltage field if needed
                pass

        yield item
