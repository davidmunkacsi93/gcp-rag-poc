"""
GCP end-to-end generation tests against real GCP services.

Prerequisites:
  - gcloud auth application-default login
  - Ingestion pipeline has been run against GCP
  - .env.gcp populated with all required values

Run:
  source .env.gcp && pytest tests/generation/e2e/ -v -m gcp
"""

import pytest

from src.generation.pipeline import generate
from src.retrieval.pipeline import retrieve

_UC01 = (
    "What were the top 3 underperforming product lines in EMEA last quarter, "
    "and is there any internal remediation guidance applicable to this region?"
)
_UC02 = (
    "Run a preliminary due diligence summary for Project Apollo — include financial "
    "exposure, open risk items, and any regulatory considerations flagged in recent reports."
)


@pytest.mark.gcp
def test_uc01_answer_is_non_empty_and_substantial():
    context = retrieve(_UC01)
    result = generate(_UC01, context)
    assert len(result.answer) >= 50


@pytest.mark.gcp
def test_uc01_has_at_least_one_citation_with_real_source_key():
    context = retrieve(_UC01)
    result = generate(_UC01, context)
    assert any(
        c.source_key and c.source_key not in ("stub_source", "")
        for c in result.citations
    )


@pytest.mark.gcp
def test_uc01_has_at_least_one_structured_citation():
    context = retrieve(_UC01)
    result = generate(_UC01, context)
    assert any(c.type == "structured" for c in result.citations)


@pytest.mark.gcp
def test_uc02_answer_is_non_empty_and_substantial():
    context = retrieve(_UC02)
    result = generate(_UC02, context)
    assert len(result.answer) >= 50


@pytest.mark.gcp
def test_uc02_has_at_least_one_semantic_citation():
    context = retrieve(_UC02)
    result = generate(_UC02, context)
    assert any(c.type == "semantic" for c in result.citations)


@pytest.mark.gcp
def test_uc02_semantic_citations_have_non_empty_source_keys():
    context = retrieve(_UC02)
    result = generate(_UC02, context)
    semantic = [c for c in result.citations if c.type == "semantic"]
    assert all(c.source_key for c in semantic)
