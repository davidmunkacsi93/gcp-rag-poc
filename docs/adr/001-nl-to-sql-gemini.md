# ADR-001 — NL-to-SQL via Gemini for Structured Retrieval

Date: 2026-03-21
Status: Accepted

---

## Context

The Structured Retriever must translate natural-language queries into SQL at runtime and execute them against BigQuery and Cloud SQL. The schema of each data source is known and stable. The query shapes are varied and unpredictable — any SQL template approach would need to cover a large and open-ended space of analyst questions.

This is the first LLM call in the runtime query path (embedding generation during ingestion is offline).

---

## Options Considered

**Option A — Rule-based SQL templates**
Pre-define a set of parameterised SQL templates matched to query patterns (e.g. "top N by metric", "filter by region"). Map incoming queries to templates using keyword matching.

- Pro: deterministic, zero latency overhead, no API cost
- Con: brittle — fails on any query shape not covered by templates; requires ongoing maintenance as requirements evolve

**Option B — Gemini LLM (stateless, single prompt)**
Prompt Gemini with the table schema and the natural-language query. Parse the returned SQL, apply a safety guard, and execute it.

- Pro: handles arbitrary query shapes without code changes; schema prompt keeps the model grounded; fast iteration
- Con: non-deterministic output; adds one Gemini API call per structured source per query; SQL correctness depends on model quality; local tests cannot use real Gemini without GCP credentials

**Option C — Dedicated NL-to-SQL model (e.g. fine-tuned SQLCoder)**
Deploy a fine-tuned SQL generation model via Vertex AI Model Garden or a managed endpoint.

- Pro: potentially higher SQL accuracy on domain-specific schemas
- Con: significantly higher operational complexity; deployment and tuning effort is disproportionate for a POC; no clear advantage over Gemini for the table schemas and query volumes involved

---

## Decision

**Option B — Gemini LLM, stateless single-prompt per data source.**

Model: `gemini-2.0-flash` (configurable via `GEMINI_MODEL` env var). One prompt per data source per query. The prompt includes the full table schema and requests a bare SQL SELECT with no markdown or explanation.

A SELECT-only safety guard (`_is_safe_sql` in `src/retrieval/structured.py`) rejects any generated SQL that does not start with `SELECT` or that contains DML/DDL keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`). Rejected SQL is returned as an error result and excluded from context fusion — it does not halt the query.

---

## Trade-offs

| | Gained | Sacrificed |
|---|---|---|
| vs. Option A | Handles any query shape; no maintenance overhead | Determinism; per-query cost; local testability without mocks |
| vs. Option C | No deployment overhead; faster iteration | Potential SQL accuracy ceiling for complex schemas |

---

## Consequences

- Every structured query incurs up to two Gemini API calls (one per data source) in addition to the Vector Search call for semantic retrieval.
- `GEMINI_MODEL` becomes a required runtime env var for GCP execution (present in `.env.gcp`). Local integration tests mock `_generate_sql` to avoid this dependency.
- SQL correctness is not guaranteed. For the POC, incorrect SQL returns an empty `StructuredResult` with an error field, which is silently excluded from context fusion. Phase 04 (Generation) should surface the gap to the user rather than returning a misleading answer.
- Upgrading to a more capable model (e.g. `gemini-1.5-pro`) or a fine-tuned SQL model requires only a `GEMINI_MODEL` env var change and no code changes.
