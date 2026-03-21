"""Tests for MockVectorStore."""

import pytest

from src.ingestion.vector_store import MockVectorStore


@pytest.fixture
def mock_store():
    return MockVectorStore()


def test_mock_vector_store_starts_with_empty_upserted_list(mock_store):
    assert mock_store.upserted == []


def test_mock_vector_store_upsert_appends_datapoints(mock_store):
    datapoints = [
        {"datapoint_id": "dp1", "feature_vector": [0.1, 0.2]},
        {"datapoint_id": "dp2", "feature_vector": [0.3, 0.4]},
    ]
    mock_store.upsert(datapoints)
    assert mock_store.upserted == datapoints


def test_mock_vector_store_upsert_called_twice_accumulates_all_datapoints(mock_store):
    first_batch = [{"datapoint_id": "dp1", "feature_vector": [0.1]}]
    second_batch = [{"datapoint_id": "dp2", "feature_vector": [0.2]}, {"datapoint_id": "dp3", "feature_vector": [0.3]}]
    mock_store.upsert(first_batch)
    mock_store.upsert(second_batch)
    assert len(mock_store.upserted) == 3
    assert mock_store.upserted == first_batch + second_batch
