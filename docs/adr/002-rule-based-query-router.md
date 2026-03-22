# ADR-002 — Rule-Based Query Router

Date: 2026-03-21
Status: Accepted

---

## Context

The Query Router must classify an incoming natural-language query and decide which retrieval paths to activate: semantic (Vector Search), structured BigQuery, structured Cloud SQL, or any combination. This decision happens on every query and is on the critical latency path.

---

## Options Considered

**Option A — Rule-based keyword matching**
Maintain frozen sets of metric-domain keywords (revenue, margin, headcount, …) and document-domain keywords (risk, remediation, guidance, …). Classify by set intersection. Activate both paths when classification is ambiguous.

- Pro: deterministic, zero latency, zero cost, fully testable without GCP, easy to reason about
- Con: vocabulary-limited — novel phrasings not in the keyword sets may misroute; adding new signals requires code changes

**Option B — LLM-based classification**
Prompt Gemini to classify the query into one of: semantic, structured, or both.

- Pro: handles arbitrary phrasing; no keyword maintenance
- Con: adds one LLM call on every query (latency + cost); non-deterministic; makes the router the most expensive component despite being the simplest conceptually; local tests require GCP credentials or additional mocking

**Option C — Hybrid (rules with LLM fallback)**
Run rule-based classification first; fall back to LLM only when confidence is low (e.g. no keyword match in either set).

- Pro: best of both for accuracy
- Con: adds complexity; the LLM fallback path still requires GCP in tests; marginal benefit over the safe-default in Option A

---

## Decision

**Option A — Pure rule-based keyword matching.**

Implemented in `src/retrieval/router.py` using two `frozenset` keyword collections and an ordered list of `doc_type` hints for filter inference. When no keyword from either set is found, both paths are activated (safe default). This ensures no query returns an empty context due to misclassification.

The `route()` function returns a `RoutingDecision` dataclass with boolean flags per path and an optional `doc_type_filter` string passed to the Semantic Retriever to restrict Vector Search results by document type.

---

## Trade-offs

| | Gained | Sacrificed |
|---|---|---|
| vs. Option B | Zero latency; zero cost; deterministic; fully unit-testable | Routing accuracy on novel phrasings outside the keyword vocabulary |
| vs. Option C | Simplicity; no conditional branching in the query path | Marginal accuracy improvement on low-confidence queries |

The safe-default (activate all paths) means a misclassified query may return more context than needed, but will not miss relevant results. Over-retrieval is acceptable in a POC where the generation layer (Phase 04) is responsible for synthesising and filtering.

---

## Consequences

- Adding new routing signals (e.g. a new document domain or data source in Phase 06) requires updating the keyword sets and `doc_type` hints in `router.py`. This is a low-effort, low-risk change.
- If routing accuracy becomes a measurable problem after Phase 04 is live, upgrading to Option B or C is straightforward: the `RoutingDecision` interface is stable, so only the `route()` implementation needs to change.
- Unit tests for the router run without GCP credentials and are fast, which keeps the local test suite self-contained.
