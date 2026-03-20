# GCP RAG POC

A proof-of-concept RAG (Retrieval-Augmented Generation) platform built on GCP, demonstrating federated retrieval across structured and unstructured data sources using Gemini.

## Docs

- [Project Overview](docs/project/overview.md)
- [Business Context & Use Cases](docs/project/business-context.md)
- [Architecture](docs/architecture/architecture.md)
- [Implementation Plan](docs/project/implementation-plan.md)

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
```

## Project Structure

```
src/                  # Application source code
tests/                # Tests
docker/               # Docker Compose for local services
docs/                 # Architecture and project documentation
scripts/              # Seed data and utility scripts
```
