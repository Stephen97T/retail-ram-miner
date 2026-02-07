from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

import scrapy
from scrapy.http import Response

from ram_miner.items import RamItem
from ram_miner.utils.extract import (
    calculate_price_per_gb,
    clean_price,
    extract_azerty_specs,
    extract_int,
)


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
            product_links = set(
                response.css("a.product-item-link::attr(href)").getall()
            )
            if not product_links:
                product_links = set(response.css("div.products a::attr(href)").getall())

            for link in product_links:
                yield response.follow(link, callback=self.parse_product)
        else:
            seen_urls = set()
            for card in product_cards:
                url = card.css("a.product-item-link::attr(href)").get()
                price = card.css(".price::text").get()

                if url and url not in seen_urls:
                    seen_urls.add(url)
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

        item["price"] = clean_price(price_raw)

        item["stock_quantity"] = extract_int(
            response.css("span.text-right::text").get()
        )
        # --- Availability ---
        item["availability"] = (
            "In Stock" if (item.get("stock_quantity") or 0) > 0 else "Out of Stock"
        )

        # --- Specs ---
        specs = extract_azerty_specs(response)
        item.update(specs)

        # Calculate derived
        item["price_per_gb"] = calculate_price_per_gb(
            item.get("price"), item.get("capacity_gb")
        )

        yield item
