# Phase 05 — Deployment

Goal: package all services as Docker containers, deploy to Cloud Run, provide a Streamlit frontend for querying, and wire up CI/CD.

> Prerequisites: Phase 04 complete. `generate(query, context)` returns a valid `GenerationResult` with answer text and citations for all query types.

---

### Stream A — Infrastructure

**A1 — Cloud Run services in Terraform**
Define three `google_cloud_run_v2_service` resources in `terraform/main.tf`:

1. `retrieval-service` — runs the retrieval HTTP wrapper
   - Service account: `rag-poc-retrieval` (already provisioned in Phase 03)
   - Min instances: 0, max instances: 2
   - Memory: 512Mi, CPU: 1
   - Port: 8080
2. `generation-service` — runs the generation HTTP wrapper
   - Service account: `rag-poc-generation` (provisioned in Phase 04)
   - Min instances: 0, max instances: 2
   - Memory: 512Mi, CPU: 1
   - Port: 8080
   - Environment variable `RETRIEVAL_SERVICE_URL` pointing to the retrieval service URL
3. `frontend` — runs the Streamlit app
   - Service account: `rag-poc-frontend` (new, minimal permissions)
   - Min instances: 0, max instances: 1
   - Memory: 256Mi, CPU: 1
   - Port: 8501
   - Environment variable `GENERATION_SERVICE_URL` pointing to the generation service URL

All three services use images from the Artifact Registry repository defined in A2.

**A2 — Artifact Registry repository**
Create a `google_artifact_registry_repository` resource in `terraform/main.tf`:
- Repository name: `rag-poc-images`
- Format: DOCKER
- Location: same region as other resources (from `var.region`)

**A3 — IAM bindings for service-to-service invocation**
- `rag-poc-frontend` service account gets `roles/run.invoker` on the `generation-service` Cloud Run service
- `rag-poc-generation` service account gets `roles/run.invoker` on the `retrieval-service` Cloud Run service
- Create the `rag-poc-frontend` service account with no additional roles beyond Cloud Run invoker

**A4 — CI/CD via Cloud Build**
Create a Cloud Build trigger on `master` branch push in `terraform/main.tf`:
- Resource: `google_cloudbuild_trigger`
- Trigger name: `rag-poc-deploy`
- Source: linked GitHub repository (or Cloud Source Repository mirror)
- Build config file: `cloudbuild.yaml` at the repository root

The trigger executes the build config defined in C5.

---

### Stream B — Local Testing Environment

**B1 — Add frontend service to docker-compose**
Add a `frontend` service to `docker/docker-compose.yml`:
- Build context: repository root, Dockerfile: `docker/Dockerfile.frontend`
- Port mapping: `8501:8501`
- Environment: `GENERATION_SERVICE_URL=http://generation-service:8080`
- Depends on: `generation-service`

**B2 — Add service containers to docker-compose**
Add a `generation-service` service to `docker/docker-compose.yml`:
- Build context: repository root, Dockerfile: `docker/Dockerfile.generation`
- Port mapping: `8080:8080`
- Environment: inherits all local env vars (`GENERATION_STUB=true`, `EMBEDDING_MODEL=stub`, Firestore emulator host, BigQuery emulator host, PostgreSQL connection vars)
- Environment: `RETRIEVAL_SERVICE_URL=http://retrieval-service:8081`
- Depends on: `retrieval-service`, `firestore`, `bigquery-emulator`, `postgres`

Add a `retrieval-service` service to `docker/docker-compose.yml`:
- Build context: repository root, Dockerfile: `docker/Dockerfile.retrieval`
- Port mapping: `8081:8080`
- Environment: inherits the same local emulator env vars
- Depends on: `firestore`, `bigquery-emulator`, `postgres`

**B3 — Local environment variable additions**
Add the following to `.env.local.example` and document in the README:
- `GENERATION_SERVICE_URL=http://localhost:8080`
- `RETRIEVAL_SERVICE_URL=http://localhost:8081`
- `FRONTEND_PORT=8501`

---

### Stream C — Core Implementation

**C1 — Streamlit frontend**
Write `src/frontend/app.py` as a single-page Streamlit application:

```python
# src/frontend/app.py
import os
import streamlit as st
import httpx

GENERATION_SERVICE_URL = os.environ.get("GENERATION_SERVICE_URL", "http://localhost:8080")
```

Features:
- Page title: "RAG Knowledge Assistant"
- Text input field with placeholder: "Ask a question about your documents and data..."
- Submit button labelled "Ask"
- On submit: show a spinner with "Retrieving context and generating answer..."
- POST `{"query": query}` to `{GENERATION_SERVICE_URL}/generate`
- On success: render `answer` as markdown; render an expandable "Sources" section (`st.expander`) listing each citation with `source_key`, `section`, and `type`
- On HTTP error or connection failure: display `st.error()` with a user-friendly message
- Do not cache responses — each query is a fresh request

**C2 — Generation service HTTP wrapper**
Write `src/generation/service.py` as a FastAPI application:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RAG Generation Service")

class GenerateRequest(BaseModel):
    query: str

class CitationResponse(BaseModel):
    source_key: str
    doc_id: str
    section: str
    type: str
    generated_sql: str

class GenerateResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    model: str
    prompt_tokens: int
```

Endpoints:
- `POST /generate` — accepts `GenerateRequest`, calls `retrieve(query)` from `src.retrieval.pipeline`, then `generate(query, context)` from `src.generation.pipeline`, returns `GenerateResponse`
- `GET /health` — returns `{"status": "healthy"}`

Run with `uvicorn src.generation.service:app --host 0.0.0.0 --port 8080`.

**C3 — Retrieval service HTTP wrapper**
Write `src/retrieval/service.py` as a FastAPI application:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RAG Retrieval Service")

class RetrieveRequest(BaseModel):
    query: str

class ContextItemResponse(BaseModel):
    type: str
    content: str
    source_ref: str
    score: float

class RetrieveResponse(BaseModel):
    items: list[ContextItemResponse]
```

Endpoints:
- `POST /retrieve` — accepts `RetrieveRequest`, calls `retrieve(query)` from `src.retrieval.pipeline`, returns `RetrieveResponse`
- `GET /health` — returns `{"status": "healthy"}`

Run with `uvicorn src.retrieval.service:app --host 0.0.0.0 --port 8080`.

**C4 — Dockerfiles**

`docker/Dockerfile.retrieval`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
EXPOSE 8080
CMD ["uvicorn", "src.retrieval.service:app", "--host", "0.0.0.0", "--port", "8080"]
```

`docker/Dockerfile.generation`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
EXPOSE 8080
CMD ["uvicorn", "src.generation.service:app", "--host", "0.0.0.0", "--port", "8080"]
```

`docker/Dockerfile.frontend`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
EXPOSE 8501
CMD ["streamlit", "run", "src/frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
```

All three Dockerfiles follow the same structure: Python 3.12 slim base, install dependencies from the shared `requirements.txt`, copy source, expose the service port, and run the entry point.

**C5 — Cloud Build config**
Write `cloudbuild.yaml` at the repository root:

```yaml
steps:
  # Build images
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/retrieval-service:${SHORT_SHA}', '-f', 'docker/Dockerfile.retrieval', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/generation-service:${SHORT_SHA}', '-f', 'docker/Dockerfile.generation', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/frontend:${SHORT_SHA}', '-f', 'docker/Dockerfile.frontend', '.']

  # Push images
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/retrieval-service:${SHORT_SHA}']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/generation-service:${SHORT_SHA}']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/frontend:${SHORT_SHA}']

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'retrieval-service', '--image', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/retrieval-service:${SHORT_SHA}', '--region', '${_REGION}', '--platform', 'managed', '--quiet']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'generation-service', '--image', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/generation-service:${SHORT_SHA}', '--region', '${_REGION}', '--platform', 'managed', '--quiet']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'frontend', '--image', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/frontend:${SHORT_SHA}', '--region', '${_REGION}', '--platform', 'managed', '--quiet']

substitutions:
  _REGION: europe-west1

options:
  logging: CLOUD_LOGGING_ONLY
```

---

### Stream D — Tests

**D1 — Streamlit frontend smoke test**
Write `tests/deployment/test_frontend_smoke.py`. Mark with `@pytest.mark.integration`.
- Start the Streamlit app in a subprocess on a random available port
- Assert the process starts without error within 10 seconds
- Assert an HTTP GET to the root URL returns status 200
- Tear down the subprocess after the test

**D2 — Generation service HTTP wrapper test**
Write `tests/deployment/test_generation_service.py`. Mark with `@pytest.mark.integration`.
- Set `GENERATION_STUB=true` and `EMBEDDING_MODEL=stub` in the test environment
- Start the FastAPI app using `httpx.ASGITransport` (in-process, no subprocess needed)
- POST `{"query": "What is the revenue for EMEA?"}` to `/generate`
- Assert response status is 200
- Assert response JSON contains `answer` (non-empty string), `citations` (list), `model` (string), `prompt_tokens` (integer)
- GET `/health` returns `{"status": "healthy"}`

**D3 — Cloud Run smoke test**
Write `tests/deployment/test_e2e_cloud_run.py`. Mark with `@pytest.mark.gcp`.
- Read service URLs from environment variables: `RETRIEVAL_SERVICE_URL`, `GENERATION_SERVICE_URL`, `FRONTEND_URL`
- Assert GET `/health` on retrieval service returns 200
- Assert GET `/health` on generation service returns 200
- Assert GET on frontend URL returns 200

**D4 — Full end-to-end manual test checklist**
The following steps must be performed manually after deployment to verify the full pipeline:

1. Open the `FRONTEND_URL` in a browser
2. Submit UC-01: "What were the top 3 underperforming product lines in EMEA last quarter, and is there any internal remediation guidance applicable to this region?"
3. Verify the answer appears within 30 seconds
4. Verify the answer contains specific product line names and references remediation guidance
5. Expand the "Sources" section and verify at least one semantic and one structured citation appear
6. Submit UC-02: "Run a preliminary due diligence summary for Project Apollo — include financial exposure, open risk items, and any regulatory considerations flagged in recent reports."
7. Verify the answer references Project Apollo by name
8. Verify citations include document source keys from Firestore

---

### New Dependencies

Add the following to `requirements.txt`:
- `streamlit>=1.40.0`
- `fastapi>=0.115.0`
- `uvicorn[standard]>=0.32.0`
- `httpx>=0.27.0`

---

### Completion Criteria

- [x] Artifact Registry repository `rag-poc-images` provisioned via Terraform
- [x] Three Cloud Run services defined in Terraform with correct service accounts and IAM bindings
- [x] `rag-poc-frontend` service account provisioned with `roles/run.invoker` on the generation service
- [x] `rag-poc-generation` service account has `roles/run.invoker` on the retrieval service
- [x] Retrieval service starts locally and responds to `POST /retrieve` with valid `RetrieveResponse` JSON
- [x] Generation service starts locally and responds to `POST /generate` with valid `GenerateResponse` JSON
- [x] Streamlit frontend starts locally on port 8501 and renders the query interface
- [x] Frontend successfully calls generation service and displays answer with citations
- [x] All three Dockerfiles build without error (`docker build -f docker/Dockerfile.<service> .`)
- [x] `docker-compose up` starts all services and the frontend is accessible at `http://localhost:8501`
- [x] `cloudbuild.yaml` is valid and Cloud Build trigger is provisioned in Terraform
- [x] Cloud Run deployment smoke test passes (`pytest -m gcp tests/deployment/`)
- [x] Manual end-to-end verification of UC-01 and UC-02 through the Streamlit frontend completes successfully
