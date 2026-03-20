# GCP RAG POC

A proof-of-concept RAG (Retrieval-Augmented Generation) platform built on GCP, demonstrating federated retrieval across structured and unstructured data sources using Gemini.

## Docs

- [Project Overview](docs/project/overview.md)
- [Business Context & Use Cases](docs/project/business-context.md)
- [Architecture](docs/architecture/architecture.md)
- [Implementation Plan](docs/project/implementation/index.md)

## Local Development

**Prerequisites:** Docker Desktop, Python 3.12+

```bash
# 1. Clone and set up environment
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Start local services
docker compose -f docker/docker-compose.yml up -d

# 3. Run smoke tests
pytest tests/test_local_services.py

# 4. Generate and load seed data
python scripts/seed/generate_structured.py
python scripts/seed/generate_documents.py
python scripts/seed/load_postgres_local.py
python scripts/seed/load_bigquery_local.py
python scripts/seed/load_gcs_local.py

# 5. Run E2E data tests
pytest tests/seed/test_e2e_local_data.py -v
```

## GCP Data Sources

**Prerequisites:** `gcloud auth application-default login`, `.env` populated with `CLOUD_SQL_*` and `GCS_BUCKET`.

```bash
# Load seed data into GCP
source .env && unset BIGQUERY_EMULATOR_HOST
python scripts/seed/load_postgres_gcp.py
python scripts/seed/load_bigquery_gcp.py
python scripts/seed/load_gcs_gcp.py

# Run GCP E2E tests
source .env && unset BIGQUERY_EMULATOR_HOST
pytest tests/seed/test_e2e_gcp_data.py -v -m gcp
```

> **Important:** `BIGQUERY_EMULATOR_HOST` in `.env` routes BigQuery calls to the local emulator.
> Always `unset BIGQUERY_EMULATOR_HOST` before running scripts or tests against real GCP.

## Project Structure

```
src/                  # Application source code
tests/                # Tests
docker/               # Docker Compose for local services
docs/                 # Architecture and project documentation
scripts/              # Seed data and utility scripts
```
