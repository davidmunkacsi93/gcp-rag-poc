# Phase 02 — Ingestion Pipeline

Goal: documents pulled from GCS are parsed, chunked, embedded via Vertex AI, and stored in the Vector Store with full metadata lineage.

---

### Stream A — Infrastructure

> Prerequisites: Phase 01 complete. GCP project provisioned.

**A1 — Provision Firestore**
Add a Firestore database to Terraform. Firestore is the metadata store — it tracks each ingested document and every chunk derived from it, including the link back to the source file. Grant the ingestion service account access.

**A2 — Provision Vertex AI Vector Search**
Add a Vector Search index and endpoint to Terraform. The index stores the embeddings produced during ingestion and is queried at retrieval time. Expose the endpoint ID as a Terraform output so the application can reference it via config. Grant the ingestion service account access.

---

### Stream B — Local Testing Environment

> Prerequisites: Stream A complete.

**B1 — Add Firestore emulator to docker-compose**
Add a Firestore emulator service to `docker/docker-compose.yml` so the ingestion pipeline can be run and tested locally without touching GCP. Extend `pytest.ini` with the emulator connection env var.

**B2 — Add embedding stub for local development**
Provide a local substitute for the Vertex AI embedding model so the pipeline can run end-to-end offline. The stub produces a deterministic vector for each input text, enabling meaningful local testing without GCP credentials.

---

### Stream C — Core Pipeline

> All pipeline modules live under `src/ingestion/`.

**C1 — GCS document reader**
Write `src/ingestion/reader.py` to list and download documents from the `raw/` prefix of the GCS bucket. Respect the `GCS_EMULATOR_HOST` env var so the same code works locally and in GCP.

**C2 — Markdown parser**
Write `src/ingestion/parser.py` to extract structure from each document: title, document type (inferred from filename), and sections split by heading. Output is a clean, structured representation of the document ready for chunking.

**C3 — Text chunker**
Write `src/ingestion/chunker.py` to split each section into overlapping fixed-size chunks. Prepend the section heading to each chunk so the embedding captures its context. Chunk size and overlap are configurable via `src/ingestion/config.py`.

**C4 — Embedder**
Write `src/ingestion/embedder.py` wrapping the Vertex AI embedding model. Process chunks in batches. Return one embedding vector per chunk. A stub implementation (see B2) is selected automatically when running locally.

**C5 — Metadata writer**
Write `src/ingestion/metadata.py` to persist document and chunk records to Firestore. Expose an idempotency check so re-running the pipeline skips documents that are already ingested. Track ingestion status (`pending`, `ingested`, `error`) per document.

**C6 — Vector Store writer**
Write `src/ingestion/vector_store.py` to upsert chunk embeddings into the Vertex AI Vector Search index. Each datapoint carries the chunk ID and enough metadata to support filtered retrieval in Phase 03 (e.g. filter by document type). A no-op mock is used in local tests.

**C7 — Pipeline orchestrator**
Write `src/ingestion/pipeline.py` as the entry point that wires all components together. For each unprocessed GCS document: read → parse → chunk → embed → write to Firestore → write to Vector Search → mark as ingested. Errors per document are logged and do not halt the run. Support a `--dry-run` flag that skips all writes.

---

### Stream D — Tests

**D1 — Unit tests: parser and chunker**
Write `tests/ingestion/test_parser.py` and `tests/ingestion/test_chunker.py` against small inline fixtures. Cover normal cases and edge cases (missing heading, single-section document, oversized section).

**D2 — Local integration test**
Write `tests/ingestion/test_e2e_local_ingestion.py` to run the full pipeline against the local Docker environment (fake-gcs-server + Firestore emulator + stub embedder + mock Vector Store). Assert that all 15 seed documents are ingested, Firestore records are created correctly, and re-running is idempotent.

Mark with `@pytest.mark.integration`.

**D3 — GCP end-to-end test**
Write `tests/ingestion/test_e2e_gcp_ingestion.py` to run the full pipeline against real GCP services. Assert that all documents are ingested and that a nearest-neighbour query returns relevant results (e.g. querying "Project Apollo risk" returns chunks from risk assessment documents).

Mark with `@pytest.mark.gcp`.

---

### Completion Criteria

- [x] Firestore and Vertex AI Vector Search provisioned via Terraform
- [x] Firestore emulator running in `docker compose up`
- [x] `run_ingestion` processes all 15 seed documents end-to-end without errors
- [x] All chunks traceable in Firestore with source lineage
- [x] Embeddings upserted to Vertex AI Vector Search index
- [x] Pipeline is idempotent — re-running does not create duplicate records
- [x] Unit and integration tests pass locally (`pytest -m "not gcp"`)
- [x] E2E GCP test passes (`pytest -m gcp tests/ingestion/`)
