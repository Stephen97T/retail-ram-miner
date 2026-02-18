# Retail RAM Miner
Automated price monitoring and analysis for RAM across major retailers (Azerty, Alternate). 
It uses Scrapy to extract data, cleans currency/spec fields, and outputs structured datasets for downstream analytics in Google BigQuery.

## Overview

- **Engine**: Scrapy (asyncio)
- **Unblocking**: Zyte API (smart proxy & browser rendering)
- **Packaging**: Docker
- **Deployment**: Google Cloud Run Job
- **Data Pipeline**: 
  - **Dev**: Local JSONL files.
  - **Prod**: 
    1. Scrapes data to local JSONL (in container).
    2. Uploads JSONL to Google Cloud Storage (GCS) for archival/state.
    3. Loads JSONL to **BigQuery** using a formatted Merge (Upsert) strategy via temporary tables.

## Prerequisites & Local Setup

### 1. Environment Configuration

Create a `.env` file or set environment variables.

```powershell
ZYTE_API_KEY=your_zyte_key_here
# Google Cloud Configuration
GCP_PROJECT_ID=your_project_id
GCP_DATASET_ID=retail_ram_data       # BigQuery Dataset ID
GCP_BUCKET_NAME=your_gcs_bucket_name # GCS Bucket for JSONL storage
# Application Settings
RUN_ENV=dev                          # 'dev' (local output) or 'prod' (GCS + BigQuery)
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json # Required for local testing of prod features
```

### 2. Install dependencies and run a crawl

```powershell
# Install dependencies from pinned requirements
uv pip install -r requirements.txt

# Run a local test crawl
scrapy crawl azerty
```

### 3. Linting & Type Safety

Ruff handles formatting/linting. Mypy enforces strict typing.

```powershell
# Run all checks
ruff check .
mypy ram_miner/
```

## Google Cloud Setup & Deployment

### 1. GCP Infrastructure Setup

Before deploying, ensure the following resources exist in your Google Cloud Project:

1.  **Project**: Create a GCP Project.
2.  **Storage**: Create a **Cloud Storage Bucket** (e.g., `ram-miner-data`) to store raw JSONL files.
3.  **BigQuery**: Create a **BigQuery Dataset** (e.g., `retail_ram_data`).
    *   *Note: Tables (`stores`, `brands`, `hardware`, `listings`, `prices`, `inventory`) will be auto-created by the pipeline if they don't exist.*
4.  **Artifact Registry**: Create a Docker repository (e.g., `retail-repo`) in your region.
5.  **Service Account**: Create a Service Account (e.g., `ram-miner-sa`) with the following IAM roles:
    *   `Storage Object Creator` (Write to GCS)
    *   `Storage Object Viewer` (Read to GCS)
    *   `BigQuery Job User` (Run query/load jobs)
    *   `BigQuery Data Editor` (Read/Write to Dataset)

### 2. Build & Push Container

```powershell
# Authenticate Docker with Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build & push image
docker build -t us-central1-docker.pkg.dev/[PROJECT_ID]/retail-repo/ram-miner:v1 .
docker push us-central1-docker.pkg.dev/[PROJECT_ID]/retail-repo/ram-miner:v1
```

### 3. Create Cloud Run Job

Create the job with the necessary environment variables. The job executes the Scrapy spider.

```powershell
gcloud run jobs create ram-miner-job \
  --image us-central1-docker.pkg.dev/[PROJECT_ID]/retail-repo/ram-miner:v1 \
  --region us-central1 \
  --tasks 1 \
  --memory 2Gi \
  --service-account=ram-miner-sa@YOUR_PROJECT.iam.gserviceaccount.com \
  --set-env-vars "^:^ZYTE_API_KEY=[KEY]:GCS_BUCKET_NAME=[BUCKET]:GCP_PROJECT_ID=[PROJECT_ID]:GCP_DATASET_ID=retail_ram_data:RUN_ENV=prod"
```

## CI/CD (GitHub Actions)

- Test: `pytest` with mocked HTTP responses
- Lint: Ruff checks formatting and unused imports
- Build: Python 3.12-slim Docker image
- Deploy: Push to Artifact Registry and update Cloud Run Job
- **Pipeline Strategy**:
  - Writes to GCS and BigQuery only on `RUN_ENV=prod`.
  - Uses **Temp Tables + MERGE** in BigQuery to deduplicate data (Upsert) based on unique keys (e.g., `store_id`, `sku`, `timestamp`).

## Troubleshooting

- **403 Forbidden (GCS/BigQuery)**: Check Service Account permissions. It needs access to both the specific Bucket and the Dataset.
- **Merge Errors**: Ensure `MERGE_KEYS` are correctly defined in `settings.py` for each table.
- **ModuleNotFoundError**: Missing `__init__.py` or `setup.py` issues.
- **MemoryLimitExceeded**: Increase Cloud Run Job memory (e.g., `2Gi` -> `4Gi`).

## License

See `LICENSE` for details.
