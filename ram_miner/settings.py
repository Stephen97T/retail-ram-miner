import os

# Project Identity
BOT_NAME = "ram_miner"
SPIDER_MODULES = ["ram_miner.spiders"]
NEWSPIDER_MODULE = "ram_miner.spiders"

# Environment Toggle
# We use os.environ.get() directly.
# Locally, you set these in your shell (e.g., $env:ENV_STATE="dev" in PowerShell)
ENV_STATE = os.environ.get("ENV_STATE", "dev").lower()

# Modern Engine Settings
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"

# Zyte API Integration (2026 Addon Style)
ADDONS = {
    "scrapy_zyte_api.Addon": 500,
}

ZYTE_API_KEY = os.environ.get("ZYTE_API_KEY")
ZYTE_API_TRANSPARENT_MODE = True

# Conditional Feed Export Logic
if ENV_STATE == "prod":
    # PRODUCTION: JSON to GCS
    BUCKET = os.environ.get("GCS_BUCKET_NAME")
    FEED_URI = f"gs://{BUCKET}/raw_data/%(name)s/%(time)s.json"
    FEED_FORMAT = "json"
else:
    # DEVELOPMENT: CSV to local data folder
    # Note: os.makedirs is safe to call even if 'data' exists
    if not os.path.exists("data"):
        os.makedirs("data")
    FEED_URI = "data/%(name)s/%(time)s.csv"
    FEED_FORMAT = "csv"

FEEDS = {
    FEED_URI: {
        "format": FEED_FORMAT,
        "encoding": "utf8",
        "store_empty": False,
    }
}

# Crawl Behavior & Throttling
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 16
DOWNLOAD_TIMEOUT = 60

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Enable or disable pipelines
ITEM_PIPELINES = {
    "ram_miner.pipeline.SplitToTablesPipeline": 300,
}
