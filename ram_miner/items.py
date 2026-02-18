import scrapy


class RamItem(scrapy.Item):
    # --- Hardware & Brand (Static Spec Data) ---
    brand = scrapy.Field()
    mpn = scrapy.Field()  # Manufacturer Part Number
    ean = scrapy.Field()  # EAN/Barcode
    capacity_gb = scrapy.Field()
    clock_speed = scrapy.Field()
    transfer_speed = scrapy.Field()
    generation = scrapy.Field()
    latency = scrapy.Field()
    modules_count = scrapy.Field()
    module_capacity_gb = scrapy.Field()
    system_of_usage = scrapy.Field()

    # --- Listing Information (Store Specific) ---
    store = scrapy.Field()
    sku = scrapy.Field()  # Store-specific ID
    name = scrapy.Field()
    url = scrapy.Field()
    image_url = scrapy.Field()
    modules = scrapy.Field()  # Raw label e.g., '2x16GB'

    # --- Pricing Information ---
    price = scrapy.Field()
    price_per_gb = scrapy.Field()
    currency = scrapy.Field()

    # --- Inventory Information ---
    availability = scrapy.Field()
    stock_quantity = scrapy.Field()
    stock_supplier = scrapy.Field()
    order_limit = scrapy.Field()

    # --- Metadata ---
    timestamp = scrapy.Field()
