"""
GCP end-to-end retrieval tests against real GCP services.

Prerequisites:
  - gcloud auth application-default login
  - Ingestion pipeline has been run: python -m src.ingestion.pipeline
  - .env.gcp populated with all required values

Run:
  source .env.gcp && pytest tests/retrieval/e2e/ -v -m gcp
"""

import pytest

from src.retrieval.pipeline import retrieve


@pytest.mark.gcp
def test_metric_query_returns_structured_results_with_rows():
    result = retrieve("What were the top 3 underperforming product lines in EMEA last quarter?")

    structured_items = [i for i in result.items if i.type == "structured"]
    assert len(structured_items) > 0
    assert all("no rows returned" not in i.content for i in structured_items)
    assert all(i.source_ref for i in structured_items)  # generated_sql is non-empty


@pytest.mark.gcp
def test_document_query_returns_remediation_chunks_with_source_lineage():
    result = retrieve("Is there any remediation guidance applicable to the Retail product line?")

    semantic_items = [i for i in result.items if i.type == "semantic"]
    assert len(semantic_items) > 0
    assert all(i.source_ref for i in semantic_items)
    assert any("remediation" in i.source_ref for i in semantic_items)


@pytest.mark.gcp
def test_due_diligence_query_retrieves_project_apollo_chunks():
    result = retrieve("Run a preliminary due diligence summary for Project Apollo")

    semantic_items = [i for i in result.items if i.type == "semantic"]
    assert len(semantic_items) > 0
    assert any(
        "apollo" in i.source_ref.lower() or "apollo" in i.content.lower()
        for i in semantic_items
    )


@pytest.mark.gcp
def test_fused_output_is_sorted_and_within_budget():
    result = retrieve("What is the financial exposure and risk outlook for Project Apollo?")

    scores = [i.score for i in result.items]
    assert scores == sorted(scores, reverse=True)
    assert len(result.items) <= 8
