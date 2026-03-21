"""
Local integration tests for the full retrieval pipeline.

Prerequisites:
  - docker compose up (Firestore emulator on :8090, BigQuery emulator on :9050, PostgreSQL on :5432)
  - Structured seed data loaded: load_postgres_local.py, load_bigquery_local.py

Run:
  source .env.local && pytest tests/retrieval/integration/ -v -m integration
"""

import os

import pytest

from src.retrieval.pipeline import retrieve


def _stub_sql_gen(schema: str, query: str) -> str:
    project_id = os.environ.get("GCP_PROJECT_ID", "gcp-rag-poc")
    if "global_metrics" in schema:
        return f"SELECT product_line, revenue_usd FROM `{project_id}.global_metrics.global_metrics` LIMIT 5"
    return "SELECT product_line, revenue_usd FROM regional.regional_metrics LIMIT 5"


@pytest.mark.integration
def test_document_query_activates_semantic_path_and_returns_chunks(monkeypatch, ingested_stub):
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)

    result = retrieve("Is there any remediation guidance for the Retail Banking product line?")

    semantic_items = [i for i in result.items if i.type == "semantic"]
    assert len(semantic_items) > 0
    assert all(i.source_ref for i in semantic_items)


@pytest.mark.integration
def test_document_query_respects_doc_type_filter(monkeypatch, ingested_stub):
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)

    result = retrieve("What are the key risk factors identified?")

    semantic_items = [i for i in result.items if i.type == "semantic"]
    assert len(semantic_items) > 0
    # All results should come from risk-related docs
    assert all("risk" in i.source_ref for i in semantic_items)


@pytest.mark.integration
def test_metric_query_activates_structured_paths_and_returns_rows(monkeypatch, ingested_stub):
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)
    monkeypatch.setattr("src.retrieval.structured._generate_sql", _stub_sql_gen)

    result = retrieve("What was the revenue by product line last quarter?")

    structured_items = [i for i in result.items if i.type == "structured"]
    assert len(structured_items) > 0
    assert all("no rows returned" not in i.content for i in structured_items)


@pytest.mark.integration
def test_federated_query_returns_results_from_both_paths(monkeypatch, ingested_stub):
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)
    monkeypatch.setattr("src.retrieval.structured._generate_sql", _stub_sql_gen)

    result = retrieve("What was the revenue growth in EMEA and is there remediation guidance?")

    semantic_items = [i for i in result.items if i.type == "semantic"]
    structured_items = [i for i in result.items if i.type == "structured"]
    assert len(semantic_items) > 0
    assert len(structured_items) > 0


@pytest.mark.integration
def test_fused_output_is_sorted_by_score_descending(monkeypatch, ingested_stub):
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)

    result = retrieve("risk assessment guidance for the project")

    scores = [i.score for i in result.items]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.integration
def test_fused_output_does_not_exceed_max_context_items(monkeypatch, ingested_stub):
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)
    monkeypatch.setattr("src.retrieval.structured._generate_sql", _stub_sql_gen)

    result = retrieve("What was the revenue growth and is there any risk or remediation guidance?")

    assert len(result.items) <= 8


@pytest.mark.integration
def test_same_query_returns_deterministic_results(monkeypatch, ingested_stub):
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)

    r1 = retrieve("Is there risk assessment guidance?")
    r2 = retrieve("Is there risk assessment guidance?")

    assert [i.source_ref for i in r1.items] == [i.source_ref for i in r2.items]
