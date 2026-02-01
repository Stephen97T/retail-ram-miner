# Retail RAM Miner
Automated price monitoring and analysis for RAM across major retailers (Azerty, Alternate). 
It uses Scrapy to extract data, cleans currency/spec fields, and outputs structured datasets for downstream analytics.

## Overview

- Engine: Scrapy (asyncio)
- Unblocking: Zyte API (smart proxy & browser rendering)
- Packaging: Docker
- Deployment: Cloud Run Job
- Data Lake: Bronze (JSON/CSV) in GCS → Gold (structured) in cloud bucket

## Prerequisites & Local Setup

### 1. Environment Configuration

Create a env variables.

```powershell
ZYTE_API_KEY=your_zyte_key_here
GCP_PROJECT_ID=your_project_id
GCS_BUCKET_NAME=your_bucket_name
```

### 2. Install dependencies and run a crawl

```powershell
# Install dependencies from pinned requirements
uv pip install -r requirements.txt

# Run a local test crawl
scrapy crawl azerty
```

### 3. Linting & Type Safety

Ruff handles formatting/linting. Mypy enforces strict typing on cleaning functions.

```powershell
# Run all checks
ruff check .
mypy ram_miner/
```

## Repository Structure

```plaintext
retail-ram-miner/
├── ram_miner/
│   ├── spiders/          # Store-specific logic (Azerty, Alternate)
│   ├── utils/            # Shared cleaning functions (price/spec parsing)
│   ├── items.py          # RAM data models
│   └── pipelines.py      # Export logic (e.g., to cloud storage/db)
├── tests/                # Pytest suite
├── pyproject.toml        # Tooling config
├── requirements.txt      # Pinned dependencies
├── Dockerfile            # Container image
└── docker-compose.yml    # Local container orchestration
```

> Note: All Python packages include `__init__.py` files for discovery (`ram_miner/`, `ram_miner/spiders/`, `ram_miner/spiders/crawlers/`, `ram_miner/utils/`, `tests/`, `tests/crawlers/`).

## Google Cloud Deployment (Cloud Run Job)

### Build & push the container image

```powershell
# Authenticate Docker with Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build & push image
docker build -t us-central1-docker.pkg.dev/[PROJECT_ID]/retail-repo/ram-miner:v1 .
docker push us-central1-docker.pkg.dev/[PROJECT_ID]/retail-repo/ram-miner:v1
```

### Create the Cloud Run Job

```powershell
gcloud run jobs create ram-miner-job \
  --image us-central1-docker.pkg.dev/[PROJECT_ID]/retail-repo/ram-miner:v1 \
  --region us-central1 \
  --memory 1Gi \
  --set-env-vars ZYTE_API_KEY=[KEY],GCS_BUCKET_NAME=[BUCKET],GCP_PROJECT_ID=[PROJECT_ID]
```

## CI/CD (GitHub Actions)

- Test: `pytest` with mocked HTTP responses
- Lint: Ruff checks formatting and unused imports
- Build: Python 3.12-slim Docker image
- Deploy: Push to Artifact Registry and update Cloud Run Job
- Concurrency:
  - `group: cd-${{ github.ref }}` ensures one active deployment per ref
  - `cancel-in-progress: true` cancels older runs for the same ref

## Troubleshooting

- 403 Forbidden: Zyte API key missing → check `.env` or Secret Manager
- ModuleNotFoundError: Missing `__init__.py` → ensure package folders have init files
- MemoryLimitExceeded: Increase Cloud Run Job memory (e.g., `2Gi`)
- Network/Version issues: Use Python 3.12 for Scrapy-only stacks

## License

See `LICENSE` for details.
