import os

# Project Identity
BOT_NAME = "ram_miner"
SPIDER_MODULES = ["ram_miner.spiders"]
NEWSPIDER_MODULE = "ram_miner.spiders"

# Environment Toggle
# We use os.environ.get() directly.
# Locally, you set these in your shell (e.g., $env:RUN_ENV="dev" in PowerShell)
RUN_ENV = os.environ.get("RUN_ENV", "dev").lower()

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

# Google Cloud Platform / BigQuery Configuration
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS"
)  # Path to service account JSON key
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_DATASET_ID = os.environ.get("GCP_DATASET_ID")
BIGQUERY_TABLE_NAMES = [
    "stores",
    "brands",
    "hardware",
    "listings",
    "prices",
    "inventory",
]
# Note: GOOGLE_APPLICATION_CREDENTIALS env var should point to your service account JSON key file

# Enable or disable pipelines
ITEM_PIPELINES = {
    "ram_miner.pipeline.SplitToTablesPipeline": 300,
}
