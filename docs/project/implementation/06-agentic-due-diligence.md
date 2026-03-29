# Phase 06 — Agentic Due Diligence

Goal: build an autonomous agent that takes an open-ended due diligence query (UC-02), plans and executes a sequence of retrieval and reasoning steps using available tools, and returns a structured report with findings, confidence indicators, and explicitly surfaced gaps.

> Prerequisites: Phase 04 complete. Retrieval and generation pipelines are functional and deployed. Phase 05 Cloud Run infrastructure is available.

---

## Phase 1 — Data Model and Tool Skeleton

**Outcome:** the agent's tool contracts are defined and each tool can be called in isolation against real or stubbed backends.

Acceptance criteria:
- Three tools exist: one for semantic document retrieval, one for structured data queries (BigQuery or Cloud SQL), one for regulatory document search
- Each tool accepts a natural-language input and returns a human-readable string suitable for passing back into a language model
- A stub mode exists that returns deterministic, fixture-quality responses without GCP credentials — activated by an environment variable, consistent with the existing embedder/generation stub pattern
- Each tool has a unit test covering: valid input returns a non-empty string, stub mode works without credentials, output contains no binary or unprintable content

**Done when:** all tool unit tests pass in both stub and real-credential mode.

---

## Phase 2 — Agent Executor and System Prompt

**Outcome:** the agent can autonomously orchestrate multi-step tool use against a Gemini model and produce a coherent final answer.

Acceptance criteria:
- An executor runs a tool-use loop: sends a query to Gemini with tool declarations, dispatches function calls to the tool registry, feeds results back, and terminates on a text response or a step limit
- The step limit prevents runaway loops — the agent stops and synthesises with whatever evidence it has collected
- Individual tool failures are caught and returned to the model as error strings rather than raising exceptions
- The system prompt instructs the agent to: gather evidence before answering, make cross-referencing tool calls, flag low-confidence findings explicitly, and produce output in a structured format parseable by Phase 3
- A unit test covers: tools are called in the order Gemini requests them, a tool error is returned to Gemini rather than raised, the loop terminates on a text response, the loop terminates at the step limit

**Done when:** executor unit tests pass and a stub end-to-end run produces a multi-step trace with a final text response.

---

## Phase 3 — Report Parser and Pipeline

**Outcome:** the agent's raw output is parsed into a typed due diligence report that downstream consumers (HTTP service, frontend) can render without string manipulation.

Acceptance criteria:
- A parser converts the agent's final text response into a structured report containing: entity name, executive summary, a list of findings (each with category, description, and confidence level), and a list of unresolved questions
- Findings categories include at minimum: financial exposure, risk items, regulatory flags, and gaps
- Confidence levels are explicit: high, medium, or low — not inferred post-hoc
- Unresolved questions are surfaced from the agent's own output, not appended externally
- A pipeline function wraps executor + parser into a single callable that takes a query and returns the structured report
- Parser unit tests cover: well-formed agent output parses to correct fields, malformed output produces a single low-confidence finding rather than failing, gaps are collected correctly

**Done when:** parser unit tests pass and the pipeline function returns a fully populated report in stub mode.

---

## Phase 4 — Services, Containers, and Infrastructure

**Outcome:** the agent is deployable alongside the existing services and the frontend exposes the due diligence workflow.

Acceptance criteria:
- An HTTP service wraps the pipeline with a POST endpoint for due diligence queries and a health endpoint
- A Dockerfile builds the agent service using the same base image and structure as the retrieval and generation services
- The agent service is added to docker-compose with stub mode enabled for local development
- A dedicated GCP service account for the agent is provisioned in Terraform with least-privilege IAM roles covering Vertex AI, Firestore, BigQuery, and Cloud SQL
- The agent service is defined as a Cloud Run service in Terraform with appropriate resource limits
- The frontend's "Due Diligence" tab calls the agent service and renders: the summary, a findings table with confidence, an expandable steps trace, and an open questions list
- The Cloud Build pipeline builds and deploys the agent service alongside the other three services

**Done when:** `docker-compose up` includes the agent service, the frontend tab renders a stub report, and Terraform plan shows the agent service account and Cloud Run resource.

---

## Phase 5 — Integration and End-to-End Validation

**Outcome:** the full agentic workflow is verified against real GCP services and UC-02 produces a credible due diligence report.

Acceptance criteria:
- A local integration test runs the full pipeline in stub mode and asserts the report contains the queried entity name, at least one finding, and at least one agent step
- A GCP end-to-end test runs UC-02 against real services and asserts: at least one financial exposure and one risk item finding, at least one high or medium confidence finding, at least one real source reference, agent executed between 2 and 8 steps, and at least one unresolved question is surfaced
- Manual verification through the Streamlit frontend: UC-02 returns a structured report with at least three findings and at least one open question

**Done when:** GCP E2E test passes and manual UC-02 verification is confirmed.

---

### Completion Criteria

- [ ] All three agent tools work in stub mode and against real GCP services
- [ ] Agent executor terminates correctly on text response and on step limit
- [ ] Pipeline returns a fully populated report for a UC-02 query
- [ ] Agent service is reachable via HTTP locally and on Cloud Run
- [ ] Frontend "Due Diligence" tab renders report, findings, steps, and open questions
- [ ] Local integration test passes with all stubs
- [ ] GCP E2E test passes and agent executes between 2 and 8 steps
- [ ] Manual UC-02 verification through Streamlit returns a structured report with at least three findings and at least one open question
