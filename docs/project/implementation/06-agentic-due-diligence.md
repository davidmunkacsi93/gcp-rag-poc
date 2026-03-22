# Phase 06 — Agentic Due Diligence

Goal: given a multi-step research task (UC-02), an agent autonomously plans and executes a sequence of retrieval and reasoning steps, accumulates evidence across multiple tool calls, and produces a structured due diligence summary with confidence indicators and explicitly surfaced gaps.

> Prerequisites: Phase 04 complete. `retrieve(query)` and `generate(query, context)` are functional. Phase 05 Cloud Run infrastructure is available for deploying the agent service.

---

### Stream A — Infrastructure

**A1 — IAM for agent service account**
Create a dedicated `rag-poc-agent` service account in Terraform with the minimum permissions needed to run the agentic workflow:

- `aiplatform.user` — call Gemini with function calling via Vertex AI
- `datastore.viewer` — read Firestore for citation resolution across agent steps
- `bigquery.dataViewer` + `bigquery.jobUser` — allow the agent's structured tool to query BigQuery directly
- `cloudsql.client` + `secretmanager.secretAccessor` — allow the agent's structured tool to query Cloud SQL

Add the service account alongside the existing generation and retrieval accounts in `terraform/main.tf`. Do not duplicate IAM role definitions — reuse existing locals.

**A2 — Cloud Run service for the agent**
Add a fourth `google_cloud_run_v2_service` resource to `terraform/main.tf` for the agent:
- Service name: `agent-service`
- Service account: `rag-poc-agent`
- Min instances: 0, max instances: 1
- Memory: 1Gi, CPU: 1 (agent loops are sequential and memory-intensive)
- Port: 8080

Grant `rag-poc-frontend` service account `roles/run.invoker` on the agent service (in addition to the generation service defined in Phase 05).

---

### Stream B — Local Testing Environment

**B1 — Stub agent tools for local testing**
Provide stub implementations for all agent tools so the full agentic loop can run without GCP credentials. The stubs must:
- Return deterministic, fixture-quality responses (e.g., a stub risk assessment document, a stub financials row)
- Be activated via `AGENT_STUB=true` environment variable using the same factory pattern as the embedder and generation stubs
- Allow the full multi-step loop to complete — the stub planner should call each tool at least once so the report formatter can be exercised end-to-end

**B2 — Add agent-service to docker-compose**
Add an `agent-service` service to `docker/docker-compose.yml`:
- Build context: repository root, Dockerfile: `docker/Dockerfile.agent`
- Port mapping: `8082:8080`
- Environment: `AGENT_STUB=true`, `GENERATION_STUB=true`, `EMBEDDING_MODEL=stub`, plus all local emulator addresses
- Depends on: `retrieval-service`, `generation-service`, `firestore`, `bigquery-emulator`, `postgres`

Update the `frontend` service in `docker-compose.yml` to add `AGENT_SERVICE_URL=http://agent-service:8082`.

---

### Stream C — Core Agent Components

> All agent modules live under `src/agent/`.

**C1 — Tool definitions**
Write `src/agent/tools.py` defining the callable tools available to the Gemini agent planner. Each tool wraps an existing pipeline function and is declared using the Vertex AI SDK's function declaration format.

Three tools:

- `retrieve_documents(query: str, doc_type: str | None) -> str` — calls `retrieve(query)` from `src.retrieval.pipeline` with the semantic path active, formats the top-k chunks as a readable string (chunk text + source key + section). Returns the formatted string to the agent.
- `query_structured_data(nl_query: str, source: str) -> str` — calls the structured retriever directly (`query_bigquery` or `query_cloudsql` depending on `source`). Returns column names, rows (capped at 20), and the generated SQL as a formatted string.
- `search_regulatory_flags(entity_name: str) -> str` — calls `retrieve_documents` with `doc_type="regulatory"` and `query=entity_name`. Returns matching chunks from regulatory documents only.

Each tool function signature must also be declared as a `vertexai.generative_models.FunctionDeclaration` so Gemini can reason about when and how to call it.

Write a `TOOL_REGISTRY: dict[str, callable]` mapping tool name strings to their Python implementations. The agent executor (C2) uses this registry to dispatch Gemini's tool call requests.

**C2 — Agent Executor**
Write `src/agent/executor.py` with the following:

```python
@dataclass
class AgentStep:
    tool_name: str
    tool_input: dict
    tool_output: str
    step_index: int

def run_agent(query: str, max_steps: int = 8) -> tuple[list[AgentStep], str]:
```

The executor implements a tool-use loop against Gemini using the Vertex AI SDK's multi-turn `chat` API with function calling enabled:

1. Initialise a `ChatSession` with the agent system prompt (see C3) and the tool declarations from C1
2. Send the user query as the first message
3. Loop up to `max_steps` times:
   a. If Gemini returns a `FunctionCall`, look up the tool in `TOOL_REGISTRY`, execute it, append an `AgentStep`, and send the result back to the chat session as a `FunctionResponse`
   b. If Gemini returns a text response with no `FunctionCall`, the loop ends — this is the agent's synthesis signal
4. Return the list of `AgentStep` objects and the final text response from Gemini

The executor must not raise on individual tool failures — catch exceptions, format them as an error string, and return them to Gemini so it can decide how to proceed.

**C3 — Agent System Prompt**
Write `src/agent/prompt.py` with:

```python
def build_agent_system_prompt() -> str:
```

The system prompt must instruct the agent to:
- Act as a due diligence research assistant for financial services
- Use the available tools to gather evidence before synthesising; do not answer from prior knowledge
- Make multiple tool calls to cross-reference findings (e.g., retrieve a document, then verify figures against structured data)
- After gathering evidence, produce a structured summary (see C4 for the expected format)
- Explicitly flag items with low confidence or missing evidence rather than interpolating
- Limit the total number of tool calls to avoid runaway loops

**C4 — DD Report Formatter**
Write `src/agent/report.py` with:

```python
@dataclass
class DDFinding:
    category: str        # "financial_exposure", "risk_item", "regulatory_flag", "gap"
    description: str
    confidence: str      # "high", "medium", "low"
    source_refs: list[str]  # source_key or "SQL" values from agent steps

@dataclass
class DDReport:
    entity: str
    summary: str
    findings: list[DDFinding]
    unresolved_questions: list[str]
    agent_steps: list[AgentStep]
    model: str

def parse_dd_report(raw_answer: str, agent_steps: list[AgentStep], entity: str, model: str) -> DDReport:
```

Parsing logic:
1. Extract the entity name from the original query (simple heuristic: noun phrase after "for" in the query)
2. Use a regex or structured prompt to parse Gemini's final answer into the `DDFinding` fields — the agent system prompt (C3) must instruct Gemini to use a parseable format (e.g., `**[FINDING: financial_exposure | high]** ...`)
3. Collect any lines prefixed with `**[GAP]**` as `unresolved_questions`
4. Populate `source_refs` for each finding from the `AgentStep` outputs that contain the relevant content
5. Return a fully populated `DDReport`

**C5 — Agent Pipeline**
Write `src/agent/pipeline.py` as the callable interface that the HTTP service and tests will use:

```python
def run_due_diligence(query: str) -> DDReport:
```

Steps:
1. Call `run_agent(query)` to get `(agent_steps, raw_answer)`
2. Call `parse_dd_report(raw_answer, agent_steps, ...)` to produce the structured report
3. Return the `DDReport`

Wire `__init__.py`:

```python
# src/agent/__init__.py
from src.agent.pipeline import run_due_diligence, DDReport
from src.agent.report import DDFinding
```

**C6 — Agent HTTP service**
Write `src/agent/service.py` as a FastAPI application:

```python
class DDRequest(BaseModel):
    query: str

class DDFindingResponse(BaseModel):
    category: str
    description: str
    confidence: str
    source_refs: list[str]

class DDReportResponse(BaseModel):
    entity: str
    summary: str
    findings: list[DDFindingResponse]
    unresolved_questions: list[str]
    steps_taken: int
    model: str
```

Endpoints:
- `POST /due-diligence` — accepts `DDRequest`, calls `run_due_diligence(query)`, returns `DDReportResponse`
- `GET /health` — returns `{"status": "healthy"}`

Run with `uvicorn src.agent.service:app --host 0.0.0.0 --port 8080`.

**C7 — Dockerfile**
Write `docker/Dockerfile.agent`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
EXPOSE 8080
CMD ["uvicorn", "src.agent.service:app", "--host", "0.0.0.0", "--port", "8080"]
```

**C8 — Streamlit frontend extension**
Extend `src/frontend/app.py` to support the agent workflow alongside the existing query interface:
- Add a tab or radio button to switch between "Ask a question" (UC-01, calls generation service) and "Due Diligence" (UC-02, calls agent service)
- In the "Due Diligence" tab: text input for the DD query, submit button, spinner during agent execution
- On success: render `summary` as markdown; render a "Findings" table (category, description, confidence); render an expandable "Steps taken" section listing each agent tool call and its output; render an "Open questions" list for `unresolved_questions`
- Add `AGENT_SERVICE_URL` env var (default: `http://localhost:8082`)

**C9 — Cloud Build update**
Add build, push, and deploy steps for `agent-service` to `cloudbuild.yaml`:
- Build: `docker/Dockerfile.agent`
- Image tag: `${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-poc-images/agent-service:${SHORT_SHA}`
- Deploy: Cloud Run `agent-service`

---

### Stream D — Tests

**D1 — Unit tests: tool definitions**
Write `tests/agent/test_tools.py`. Cover:
- Each tool function returns a non-empty string when called with valid inputs (using stubs)
- `retrieve_documents` with `doc_type="regulatory"` only returns chunks tagged regulatory
- `query_structured_data` with `source="bigquery"` invokes the BigQuery path, not Cloud SQL
- Tool output strings are parseable by the agent (no binary or unprintable content)

**D2 — Unit tests: DD report parser**
Write `tests/agent/test_report.py` with synthetic Gemini response fixtures. Cover:
- A response containing `**[FINDING: financial_exposure | high]**` lines is parsed into correct `DDFinding` objects
- `**[GAP]**` lines are collected as `unresolved_questions`
- A response with no structured markers produces a single finding with `confidence = "low"` and the full text as the description
- `source_refs` are populated from matching agent step outputs

**D3 — Unit tests: agent executor loop**
Write `tests/agent/test_executor.py` using a stub Gemini chat session that returns a scripted sequence of function calls followed by a final text response. Cover:
- The loop calls exactly the tools Gemini requests, in order
- A tool execution error is returned to Gemini as an error string rather than raising
- The loop terminates when Gemini returns a text response (no function call)
- The loop terminates at `max_steps` even if Gemini keeps requesting tool calls

**D4 — Local integration test**
Write `tests/agent/test_e2e_local_agent.py` to run the full `run_due_diligence` pipeline against the local Docker environment. Mark with `@pytest.mark.integration`.

Setup: set `AGENT_STUB=true`, `GENERATION_STUB=true`, `EMBEDDING_MODEL=stub`.

Assertions:
- `run_due_diligence("Run a preliminary due diligence summary for Project Apollo — include financial exposure, open risk items, and any regulatory considerations flagged in recent reports.")` returns a `DDReport`
- `DDReport.entity` contains "Apollo"
- `DDReport.findings` is non-empty
- At least one `AgentStep` was executed (agent called at least one tool)
- `DDReport.model` is a non-empty string

**D5 — GCP end-to-end test**
Write `tests/agent/test_e2e_gcp_agent.py` to run the full pipeline against real GCP services. Mark with `@pytest.mark.gcp`.

Assertions for UC-02 ("Run a preliminary due diligence summary for Project Apollo — include financial exposure, open risk items, and any regulatory considerations flagged in recent reports."):
- `DDReport.findings` contains at least one `financial_exposure` finding and at least one `risk_item` finding
- At least one finding has `confidence` set to "high" or "medium" (evidence was found)
- At least one `source_ref` is a real GCS key or "SQL" (not a stub value)
- Agent executed between 2 and 8 steps (bounded, not runaway)
- `unresolved_questions` is present (agent surfaced at least one gap)

---

### Completion Criteria

- [ ] `rag-poc-agent` service account provisioned via Terraform with correct IAM roles
- [ ] `agent-service` Cloud Run service defined in Terraform with `rag-poc-agent` service account
- [ ] `rag-poc-frontend` service account has `roles/run.invoker` on the agent service
- [ ] All three agent tools (`retrieve_documents`, `query_structured_data`, `search_regulatory_flags`) return parseable strings for valid inputs
- [ ] Agent executor loop terminates correctly on text response and on `max_steps` guard
- [ ] `run_due_diligence(query)` returns a `DDReport` with at least one finding
- [ ] DD report parser extracts findings, confidence, and gaps from a Gemini-format response
- [ ] Stub mode (`AGENT_STUB=true`) allows the full loop to run without GCP credentials
- [ ] `docker-compose up` includes `agent-service` accessible at `http://localhost:8082`
- [ ] Streamlit frontend "Due Diligence" tab renders summary, findings table, agent steps, and open questions
- [ ] Unit tests pass locally (`pytest tests/agent/test_tools.py tests/agent/test_report.py tests/agent/test_executor.py`)
- [ ] Local integration test passes with all stubs (`pytest -m integration tests/agent/`)
- [ ] GCP E2E test passes and agent executes between 2 and 8 steps (`pytest -m gcp tests/agent/`)
- [ ] Manual verification: UC-02 query through the Streamlit "Due Diligence" tab returns a structured report with at least three findings and at least one open question
