# GCP RAG POC

A proof-of-concept RAG (Retrieval-Augmented Generation) platform built on GCP, demonstrating federated retrieval across structured and unstructured data sources using Gemini.

## Docs

- [Project Overview](docs/project/overview.md)
- [Business Context & Use Cases](docs/project/business-context.md)
- [Architecture](docs/architecture/architecture.md)
- [Infrastructure](docs/architecture/infrastructure.md)
- [Implementation Plan](docs/project/implementation/index.md)

## Environment Setup

Two env files control which services are used. Copy the examples and fill in any blanks:

```bash
cp .env.local.example .env.local   # local Docker emulators — values pre-filled
cp .env.gcp.example .env.gcp       # real GCP services — fill from: cd terraform && terraform output
```

Both files are gitignored. Never commit credentials.

## Local Development

**Prerequisites:** Docker Desktop, Python 3.12+

```bash
# 1. Set up Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Start local services
docker compose -f docker/docker-compose.yml up -d

# 3. Run smoke tests
source .env.local && pytest tests/test_local_services.py

# 4. Generate and load seed data
source .env.local
python scripts/seed/generate_structured.py
python scripts/seed/generate_documents.py
python scripts/seed/load_postgres_local.py
python scripts/seed/load_bigquery_local.py
python scripts/seed/load_gcs_local.py

# 5. Run local tests
source .env.local && pytest -m "not gcp" -v
```

## GCP

**Prerequisites:** `gcloud auth application-default login`, `terraform apply` complete.

```bash
# Load seed data into GCP
source .env.gcp
python scripts/seed/load_postgres_gcp.py
python scripts/seed/load_bigquery_gcp.py
python scripts/seed/load_gcs_gcp.py

# Run ingestion pipeline
source .env.gcp && python -m src.ingestion.pipeline

# Run GCP E2E tests
source .env.gcp && pytest -m gcp -v
```

## Project Structure

```
src/                  # Application source code
tests/                # Tests
docker/               # Docker Compose for local services
docs/                 # Architecture and project documentation
scripts/              # Seed data and utility scripts
```
