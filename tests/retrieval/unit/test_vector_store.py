"""Unit tests for the retrieval StubVectorSearchClient."""

import pytest

from src.retrieval.vector_store import StubVectorSearchClient


def _datapoint(dp_id: str, vector: list[float], doc_type: str = "strategy_memo") -> dict:
    return {
        "datapoint_id": dp_id,
        "feature_vector": vector,
        "restricts": [
            {"namespace": "doc_type", "allow_list": [doc_type]},
        ],
    }


@pytest.fixture
def stub():
    return StubVectorSearchClient()


def test_find_neighbors_returns_results_sorted_by_dot_product_descending(stub):
    stub.upsert([
        _datapoint("a", [1.0, 0.0]),
        _datapoint("b", [0.0, 1.0]),
        _datapoint("c", [0.8, 0.6]),
    ])
    # query aligns with "a" most closely
    results = stub.find_neighbors([1.0, 0.0], top_k=3)
    assert [r.id for r in results] == ["a", "c", "b"]


def test_find_neighbors_respects_top_k(stub):
    stub.upsert([_datapoint(str(i), [float(i), 0.0]) for i in range(10)])
    results = stub.find_neighbors([1.0, 0.0], top_k=3)
    assert len(results) == 3


def test_find_neighbors_filters_by_doc_type(stub):
    stub.upsert([
        _datapoint("risk_1", [1.0, 0.0], doc_type="risk_assessment"),
        _datapoint("strat_1", [0.9, 0.0], doc_type="strategy_memo"),
        _datapoint("risk_2", [0.8, 0.0], doc_type="risk_assessment"),
    ])
    results = stub.find_neighbors([1.0, 0.0], top_k=5, doc_type_filter="risk_assessment")
    ids = [r.id for r in results]
    assert "strat_1" not in ids
    assert "risk_1" in ids
    assert "risk_2" in ids


def test_find_neighbors_returns_empty_when_filter_matches_nothing(stub):
    stub.upsert([_datapoint("a", [1.0, 0.0], doc_type="strategy_memo")])
    results = stub.find_neighbors([1.0, 0.0], doc_type_filter="regulatory")
    assert results == []


def test_upsert_replaces_existing_datapoint_with_same_id(stub):
    stub.upsert([_datapoint("a", [1.0, 0.0])])
    stub.upsert([_datapoint("a", [0.0, 1.0])])  # overwrite with different vector
    results = stub.find_neighbors([1.0, 0.0], top_k=1)
    assert len(results) == 1
    # original vector [1.0, 0.0] replaced — dot product with [1.0, 0.0] is now 0.0
    assert results[0].distance == pytest.approx(0.0)


def test_upsert_deduplication_does_not_grow_datapoint_count(stub):
    stub.upsert([_datapoint("a", [1.0, 0.0]), _datapoint("b", [0.0, 1.0])])
    stub.upsert([_datapoint("a", [0.5, 0.5])])  # re-upsert "a"
    results = stub.find_neighbors([1.0, 1.0], top_k=10)
    assert len(results) == 2


def test_find_neighbors_distance_equals_dot_product(stub):
    stub.upsert([_datapoint("a", [0.6, 0.8])])
    results = stub.find_neighbors([1.0, 0.0], top_k=1)
    assert results[0].distance == pytest.approx(0.6)
