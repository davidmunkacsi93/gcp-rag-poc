"""
Self-contained GCP end-to-end test for the full ingest → retrieve → generate pipeline.

The conftest ingests two controlled test documents (Project Zenith) into real GCP
services before this module runs, and tears them down afterwards.

pytest-retry handles Vertex AI Vector Search propagation delay: vectors are
queryable within ~2 minutes of upsert in STREAM_UPDATE mode.

Run:
  pytest tests/e2e/ -v -m gcp
"""

import pytest

from src.generation.pipeline import generate
from src.retrieval.pipeline import retrieve

_SEMANTIC_QUERY = (
    "What remediation actions are recommended for Project Zenith, "
    "and what are the key risks identified?"
)
_STRUCTURED_QUERY = (
    "What were the top 3 underperforming product lines in EMEA last quarter?"
)
_FEDERATED_QUERY = (
    "What are the regulatory risks for Project Zenith and which EMEA product "
    "lines are underperforming?"
)


@pytest.mark.gcp
@pytest.mark.retry(retries=5, delay=30)
def test_semantic_query_returns_grounded_answer(pipeline_data):
    context = retrieve(_SEMANTIC_QUERY)

    semantic_items = [i for i in context.items if i.type == "semantic"]
    assert semantic_items, "No semantic context items — Vector Search may still be propagating"

    result = generate(_SEMANTIC_QUERY, context)

    assert len(result.answer) >= 50
    assert result.prompt_tokens > 0
    assert result.model


@pytest.mark.gcp
@pytest.mark.retry(retries=5, delay=30)
def test_semantic_query_cites_ingested_test_documents(pipeline_data):
    context = retrieve(_SEMANTIC_QUERY)

    semantic_items = [i for i in context.items if i.type == "semantic"]
    assert semantic_items, "No semantic context items — Vector Search may still be propagating"

    result = generate(_SEMANTIC_QUERY, context)

    assert any(c.type == "semantic" for c in result.citations)
    assert any(
        "zenith" in c.source_key.lower()
        for c in result.citations
        if c.type == "semantic"
    )


@pytest.mark.gcp
def test_structured_query_returns_grounded_answer(pipeline_data):
    context = retrieve(_STRUCTURED_QUERY)

    structured_items = [i for i in context.items if i.type == "structured"]
    assert structured_items, "No structured context items returned"

    result = generate(_STRUCTURED_QUERY, context)

    assert len(result.answer) >= 50
    assert any(c.type == "structured" for c in result.citations)


@pytest.mark.gcp
@pytest.mark.retry(retries=5, delay=30)
def test_federated_query_retrieves_both_paths(pipeline_data):
    context = retrieve(_FEDERATED_QUERY)

    semantic_items = [i for i in context.items if i.type == "semantic"]
    structured_items = [i for i in context.items if i.type == "structured"]

    assert semantic_items, "No semantic items — Vector Search may still be propagating"
    assert structured_items, "No structured items returned"


@pytest.mark.gcp
@pytest.mark.retry(retries=5, delay=30)
def test_full_pipeline_generation_result_is_well_formed(pipeline_data):
    context = retrieve(_SEMANTIC_QUERY)

    semantic_items = [i for i in context.items if i.type == "semantic"]
    assert semantic_items, "No semantic context items — Vector Search may still be propagating"

    result = generate(_SEMANTIC_QUERY, context)

    assert result.answer
    assert isinstance(result.citations, list)
    assert result.model
    assert result.prompt_tokens > 0
