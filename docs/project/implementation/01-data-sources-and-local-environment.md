# Phase 01 — Data Sources & Local Environment

Goal: all three data sources exist in GCP and locally, populated with realistic synthetic financial services data.

---

### Stream A — Local Docker Environment

**A1 — Scaffold docker-compose**
Set up `docker/docker-compose.yml` with three services: `postgres` (Cloud SQL / Snowflake substitute), `fake-gcs-server` (GCS / Box substitute), `bigquery-emulator`. Include a shared network and volume mounts for seed data.

**A2 — Validate local services**
Confirm each container starts cleanly and is reachable from the host. Write a smoke-test script (`scripts/check_local.py`) that connects to each service and asserts availability.

---

### Stream B — Synthetic Seed Data

**B1 — Generate structured data**
Write `scripts/seed/generate_structured.py` using `faker` to produce:
- `global_metrics` — enterprise KPIs, product line performance, quarterly P&L (→ BigQuery)
- `regional_metrics` — regional P&L, product-level breakdown by geography (→ Cloud SQL)

Output: two CSV files under `data/seed/`.

**B2 — Generate unstructured documents**
Write `scripts/seed/generate_documents.py` to produce 10–15 realistic synthetic documents:
- Internal strategy memos
- Risk assessment reports (including one for "Project Apollo")
- Remediation guidance by product line

Output: Markdown files under `data/seed/documents/`.

---

### Stream C — GCP Data Sources

> Prerequisites: Stream B complete. GCP project `gcp-rag-poc` exists.

**C1 — Provision GCS bucket (Box substitute)**
Create a GCS bucket `rag-poc-documents-dev` in Terraform. Define folder structure: `/raw`, `/ingested`. Upload seed documents from `data/seed/documents/`.

**C2 — Provision BigQuery dataset**
Create dataset `global_metrics` in Terraform. Define and load `global_metrics` table from seed CSV.

**C3 — Provision Cloud SQL (Snowflake substitute)**
Create a Cloud SQL PostgreSQL instance `rag-poc-regional-dev` in Terraform. Create schema `regional` with table `regional_metrics`. Load from seed CSV.

**C4 — IAM & secrets**
Create a service account `rag-poc-ingestion@...` with least-privilege roles for GCS, BigQuery, and Cloud SQL. Store Cloud SQL credentials in Secret Manager.

---

### Stream D — Local Data Sources (mirror of Stream C)

> Prerequisites: Stream A complete, Stream B complete.

**D1 — Load BigQuery emulator**
Write `scripts/seed/load_bigquery_local.py` to create dataset and load seed CSVs into the local BigQuery emulator.

**D2 — Load PostgreSQL**
Write `scripts/seed/load_postgres_local.py` to create schema and load seed CSVs into the local Postgres container.

**D3 — Load fake-gcs-server**
Write `scripts/seed/load_gcs_local.py` to upload seed documents to the local GCS emulator bucket.

---

### Completion Criteria

- [ ] `docker compose up` starts all three local services cleanly
- [ ] Smoke tests pass against local environment
- [ ] All three GCP resources provisioned via Terraform and queryable
- [ ] Seed data present in all six data sources (3 local, 3 GCP)
- [ ] Service account and secrets configured in GCP
