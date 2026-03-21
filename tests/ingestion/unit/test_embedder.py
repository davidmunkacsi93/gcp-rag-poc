"""Tests for the embedder module."""

import math

import pytest
from src.ingestion.embedder import StubEmbedder, VertexEmbedder, get_embedder


@pytest.fixture
def embedder():
    return StubEmbedder()


def test_embed_returns_one_vector_per_input_text(embedder):
    texts = ["hello world", "foo bar", "baz"]
    result = embedder.embed(texts)
    assert len(result) == len(texts)


def test_embed_each_vector_has_768_elements(embedder):
    result = embedder.embed(["some text", "another text"])
    for vector in result:
        assert len(vector) == 768


def test_embed_each_vector_is_unit_vector(embedder):
    result = embedder.embed(["normalised text", "second text"])
    for vector in result:
        norm = math.sqrt(sum(v * v for v in vector))
        assert abs(norm - 1.0) < 1e-6


def test_embed_same_input_produces_same_vector(embedder):
    text = "deterministic input"
    first = embedder.embed([text])
    second = embedder.embed([text])
    assert first == second


def test_embed_different_inputs_produce_different_vectors(embedder):
    result = embedder.embed(["text alpha", "text beta"])
    assert result[0] != result[1]


def test_embed_works_with_single_element_list(embedder):
    result = embedder.embed(["only one"])
    assert len(result) == 1
    assert len(result[0]) == 768


def test_embed_works_with_empty_list(embedder):
    result = embedder.embed([])
    assert result == []


def test_get_embedder_returns_stub_embedder_when_model_is_stub():
    embedder = get_embedder(model="stub")
    assert isinstance(embedder, StubEmbedder)


def test_get_embedder_returns_vertex_embedder_when_model_is_not_stub():
    embedder = get_embedder(model="text-embedding-004")
    assert isinstance(embedder, VertexEmbedder)
