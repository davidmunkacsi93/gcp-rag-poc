# Phase 03 — Retrieval

Goal: a query is routed to the correct retrieval paths — semantic search against the Vector Store and NL-to-SQL against BigQuery and Cloud SQL — with results fused and re-ranked into a ranked context list ready for generation.

> Prerequisites: Phase 02 complete. All 15 seed documents ingested into Vertex AI Vector Search and Firestore.

---

### Stream A — Infrastructure

**A1 — IAM for retrieval service account**
Create a dedicated `rag-poc-retrieval` service account in Terraform with the minimum permissions needed to serve queries:

- `aiplatform.user` — read from Vertex AI Vector Search
- `datastore.user` — read chunk and document records from Firestore
- `bigquery.dataViewer` + `bigquery.jobUser` — run NL-to-SQL queries against BigQuery
- `cloudsql.client` — connect to Cloud SQL for NL-to-SQL queries
- `secretmanager.secretAccessor` — read the Cloud SQL password from Secret Manager

Grant existing roles where already defined; do not duplicate Terraform resources.

---

### Stream B — Local Testing Environment

**B1 — Add Vector Search stub for local development**
Provide a local substitute for Vertex AI Vector Search's `find_neighbors` query API. The stub stores upserted datapoints in-memory during the test session and responds to nearest-neighbour queries by returning the top-K by cosine similarity against the query embedding. This enables retrieval tests to run end-to-end without GCP credentials.

Wire the stub through the same environment-variable switch used by the ingestion `MockVectorStore`, so no test code needs to branch on environment.

**B2 — Verify local structured data is queryable**
Confirm that the BigQuery emulator and local PostgreSQL instance have the seed data loaded (from Phase 01) and are accessible at the addresses defined in `pytest.ini`. Add a pytest fixture that fails fast with a clear message if either service is unreachable, so retrieval tests give immediate diagnostic feedback rather than obscure SQL errors.

---

### Stream C — Core Retrieval Components

> All retrieval modules live under `src/retrieval/`.

**C1 — Query Router**
Write `src/retrieval/router.py` to classify an incoming natural-language query and return a `RoutingDecision` that specifies which retrieval paths to activate.

Routing logic (rule-based for the POC, no LLM call):
- If the query contains explicit metric or financial keywords (revenue, margin, growth, headcount, quarter, region, YoY) → activate structured path
- If the query references documents, reports, guidance, policy, risk, or remediation → activate semantic path
- If neither signal is clear, activate both paths (safe default)

`RoutingDecision` carries:
- `semantic: bool`
- `structured_bigquery: bool`
- `structured_cloudsql: bool`
- `doc_type_filter: str | None` — optional filter to pass to the semantic retriever (e.g. `risk_assessment`, `remediation`, `regulatory`)

**C2 — Semantic Retriever**
Write `src/retrieval/semantic.py` to query the Vector Store and resolve chunk metadata from Firestore.

Steps:
1. Embed the query using the same embedder interface as ingestion (`VertexEmbedder` in GCP, `StubEmbedder` locally)
2. Call `find_neighbors` on the deployed Vector Search index, passing `top_k` (configurable, default 5) and any `doc_type_filter` from the routing decision as a restricts filter
3. For each returned datapoint, look up the corresponding Firestore chunk record to retrieve: `text`, `section`, `doc_id`, `source_key`, `doc_type`
4. Return a list of `SemanticResult` objects: `chunk_id`, `text`, `section`, `doc_id`, `source_key`, `score`

**C3 — Structured Retriever**
Write `src/retrieval/structured.py` to translate the natural-language query into SQL and execute it against BigQuery and/or Cloud SQL.

NL-to-SQL approach for the POC: prompt Gemini with the table schema and the query, then execute the returned SQL. Keep the interaction stateless — one prompt per query per data source.

Implement two functions:

- `query_bigquery(nl_query: str) -> StructuredResult` — generates and runs SQL against the `global_metrics` dataset; returns column names, rows (capped at 50), and the generated SQL for transparency
- `query_cloudsql(nl_query: str) -> StructuredResult` — same pattern against the Cloud SQL `regional` database

Both functions must:
- Validate that the generated SQL is a `SELECT` statement before execution (reject any DML/DDL)
- Surface the generated SQL in the result so it can be included in the context for citation
- Handle SQL errors gracefully — return an empty result with an error message rather than raising

**C4 — Context Fusion**
Write `src/retrieval/fusion.py` to merge results from all active retrieval paths into a single ranked context list.

Fusion logic:
1. Collect all `SemanticResult` and `StructuredResult` objects from whichever paths fired
2. De-duplicate semantic chunks by `chunk_id` (take the highest-scored copy)
3. Assign a unified relevance score: semantic chunks use their Vector Search distance score; structured results use a fixed score of 1.0 (they were explicitly requested by the router)
4. Sort descending by relevance score
5. Truncate to a configurable `max_context_items` (default 8) to stay within downstream prompt budget
6. Return a `FusedContext` object: ordered list of `ContextItem` objects (type, content, source reference, score)

**C5 — Retrieval pipeline entry point**
Write `src/retrieval/pipeline.py` as the callable interface that the generation layer (Phase 04) and tests will use.

```python
def retrieve(query: str) -> FusedContext:
    decision = route(query)
    results = []
    if decision.semantic:
        results += semantic_retrieve(query, doc_type_filter=decision.doc_type_filter)
    if decision.structured_bigquery:
        results += [query_bigquery(query)]
    if decision.structured_cloudsql:
        results += [query_cloudsql(query)]
    return fuse(results)
```

Expose `retrieve` as the single public API of the retrieval package. No caller should need to import individual components.

---

### Stream D — Tests

**D1 — Unit tests: router**
Write `tests/retrieval/test_router.py` against inline query fixtures. Cover:
- Query with metric keywords → structured paths activated
- Query with document/guidance keywords → semantic path activated
- Ambiguous query → both paths activated
- `doc_type_filter` is correctly inferred from document-domain keywords (e.g. "risk" → `risk_assessment`)

**D2 — Unit tests: context fusion**
Write `tests/retrieval/test_fusion.py` with synthetic `SemanticResult` and `StructuredResult` fixtures. Cover:
- Duplicate chunk IDs — only the highest-scored copy is retained
- Results are sorted by score descending
- Truncation at `max_context_items`
- Mixed semantic + structured results appear in the fused output

**D3 — Unit tests: structured retriever SQL safety**
Write `tests/retrieval/test_structured.py` to assert that any generated SQL containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, or `CREATE` is rejected before execution, regardless of casing.

**D4 — Local integration test**
Write `tests/retrieval/test_e2e_local_retrieval.py` to run the full retrieval pipeline against the local Docker environment (stub embedder + in-memory Vector Search stub + BigQuery emulator + local PostgreSQL). Mark with `@pytest.mark.integration`.

Assertions:
- A metric-focused query activates at least one structured path and returns rows from the relevant table
- A document-focused query activates the semantic path and returns at least one chunk with a traceable `source_key`
- A federated query (both document and metric keywords) returns results from both paths in the fused output
- The fused output is sorted by score and does not exceed `max_context_items`
- Re-running the same query returns the same results (deterministic with stub embedder)

**D5 — GCP end-to-end test**
Write `tests/retrieval/test_e2e_gcp_retrieval.py` to run the full retrieval pipeline against real GCP services. Mark with `@pytest.mark.gcp`.

Assertions:
- *"What were the top 3 underperforming product lines in EMEA last quarter?"* → structured path returns rows from Cloud SQL and/or BigQuery
- *"Is there any remediation guidance applicable to the Retail product line?"* → semantic path returns chunks from remediation documents with `doc_type == remediation`
- *"Run a preliminary due diligence summary for Project Apollo"* → both paths fire; semantic results include chunks from the Project Apollo risk assessment document

---

### Completion Criteria

- [ ] Retrieval service account provisioned via Terraform with least-privilege IAM
- [ ] `retrieve(query)` returns a `FusedContext` for all three query types (semantic, structured, federated)
- [ ] SQL injection guard rejects any non-SELECT generated SQL before execution
- [ ] Context fusion de-duplicates chunks and enforces the `max_context_items` budget
- [ ] Unit and integration tests pass locally (`pytest -m "not gcp"`)
- [ ] E2E GCP test passes (`pytest -m gcp tests/retrieval/`)
- [ ] All retrieval results carry a `source_key` or `generated_sql` field sufficient for Phase 04 citation assembly
