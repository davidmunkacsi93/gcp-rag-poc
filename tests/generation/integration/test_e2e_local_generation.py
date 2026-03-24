"""
Local integration tests for the full retrieve-then-generate pipeline.

Prerequisites:
  - docker compose up (Firestore emulator on :8090)
  - source .env.local

Run:
  source .env.local && pytest tests/generation/integration/ -v -m integration
"""

import pytest

from src.generation.config import GenerationConfig
from src.generation.pipeline import generate
from src.retrieval.pipeline import retrieve


@pytest.mark.integration
def test_document_query_returns_non_empty_answer(monkeypatch, ingested_stub):
    monkeypatch.setenv("GENERATION_STUB", "true")
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)

    context = retrieve("Is there any remediation guidance for the Retail Banking product line?")
    result = generate("Is there any remediation guidance for the Retail Banking product line?", context)

    assert result.answer


@pytest.mark.integration
def test_document_query_returns_at_least_one_citation(monkeypatch, ingested_stub):
    monkeypatch.setenv("GENERATION_STUB", "true")
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)

    context = retrieve("Is there any remediation guidance for the Retail Banking product line?")
    result = generate("Is there any remediation guidance for the Retail Banking product line?", context)

    assert len(result.citations) >= 1


@pytest.mark.integration
def test_generation_result_model_matches_config(monkeypatch, ingested_stub):
    monkeypatch.setenv("GENERATION_STUB", "true")
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)

    context = retrieve("What are the key risk factors identified?")
    result = generate("What are the key risk factors identified?", context)

    assert result.model == GenerationConfig.from_env().model_name


@pytest.mark.integration
def test_generation_result_prompt_tokens_is_positive(monkeypatch, ingested_stub):
    monkeypatch.setenv("GENERATION_STUB", "true")
    monkeypatch.setattr("src.retrieval.pipeline.get_vector_search_client", lambda *a, **kw: ingested_stub)

    context = retrieve("What are the key risk factors identified?")
    result = generate("What are the key risk factors identified?", context)

    assert result.prompt_tokens > 0
