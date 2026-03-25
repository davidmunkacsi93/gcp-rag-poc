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

    zenith_items = [i for i in semantic_items if "zenith" in i.source_ref.lower()]
    assert zenith_items, (
        f"Zenith documents not in top-k context (retrieval issue, not citation issue). "
        f"source_refs returned: {[i.source_ref for i in semantic_items]}"
    )

    result = generate(_SEMANTIC_QUERY, context)

    assert any(c.type == "semantic" for c in result.citations)
    assert any(
        "zenith" in c.source_key.lower()
        for c in result.citations
        if c.type == "semantic"
    ), (
        f"LLM did not cite zenith documents. citations: {[(c.source_key, c.type) for c in result.citations]}"
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
def test_full_pipeline_generation_result_is_well_formed(pipeline_data):
    context = retrieve(_SEMANTIC_QUERY)

    semantic_items = [i for i in context.items if i.type == "semantic"]
    assert semantic_items, "No semantic context items — Vector Search may still be propagating"

    result = generate(_SEMANTIC_QUERY, context)

    assert result.answer
    assert isinstance(result.citations, list)
    assert result.model
    assert result.prompt_tokens > 0
