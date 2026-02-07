import scrapy


class RamItem(scrapy.Item):
    # Primary Data
    name = scrapy.Field()  # Full product title
    price = scrapy.Field()  # Cleaned float (e.g., 120.50)
    price_per_gb = scrapy.Field()  # Derived float (e.g., 3.76)
    currency = scrapy.Field()  # 'EUR'
    store = scrapy.Field()  # 'Azerty' or 'Alternate'

    # Technical Specs (For SQL Filtering)
    capacity_gb = scrapy.Field()  # Integer (e.g., 32)
    speed_mhz = scrapy.Field()  # Integer (e.g., 6000)
    generation = scrapy.Field()  # 'DDR4' or 'DDR5'
    latency = scrapy.Field()  # Integer '30' (CL30)
    modules = scrapy.Field()  # Raw label, e.g., '2x16GB'
    modules_count = scrapy.Field()  # Parsed integer count, e.g., 2
    module_capacity_gb = scrapy.Field()  # Parsed per-module capacity, e.g., 16
    system_of_usage = scrapy.Field()  # Raw label, e.g., 'PC' or 'Laptop'

    # Store Info
    availability = scrapy.Field()  # 'In Stock' or 'Out of Stock'
    stock_quantity = scrapy.Field()  # Integer or None if unknown
    stock_supplier = scrapy.Field()  # Integer or None if unknown
    order_limit = scrapy.Field()  # Max units per order, if any

    # Metadata & Links
    url = scrapy.Field()  # Source link
    sku = scrapy.Field()  # Store-specific ID
    timestamp = scrapy.Field()  # When it was scraped
    image_url = scrapy.Field()  # For visual reference
