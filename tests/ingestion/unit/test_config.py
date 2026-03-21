"""Tests for the IngestionConfig module."""

import pytest

from src.ingestion.config import IngestionConfig


def test_from_env_reads_gcs_bucket(monkeypatch):
    monkeypatch.setenv("GCS_DOCUMENTS_BUCKET", "my-bucket")
    config = IngestionConfig.from_env()
    assert config.gcs_bucket == "my-bucket"


def test_from_env_reads_raw_prefix(monkeypatch):
    monkeypatch.setenv("GCS_RAW_PREFIX", "custom-raw/")
    config = IngestionConfig.from_env()
    assert config.raw_prefix == "custom-raw/"


def test_from_env_reads_processed_prefix(monkeypatch):
    monkeypatch.setenv("GCS_PROCESSED_PREFIX", "custom-processed/")
    config = IngestionConfig.from_env()
    assert config.processed_prefix == "custom-processed/"


def test_from_env_reads_chunk_size(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "1000")
    config = IngestionConfig.from_env()
    assert config.chunk_size == 1000


def test_from_env_reads_chunk_overlap(monkeypatch):
    monkeypatch.setenv("CHUNK_OVERLAP", "100")
    config = IngestionConfig.from_env()
    assert config.chunk_overlap == 100


def test_from_env_reads_embedding_model(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-004")
    config = IngestionConfig.from_env()
    assert config.embedding_model == "text-embedding-004"


def test_from_env_reads_vertex_location(monkeypatch):
    monkeypatch.setenv("VERTEX_AI_LOCATION", "us-central1")
    config = IngestionConfig.from_env()
    assert config.vertex_location == "us-central1"


def test_from_env_reads_index_endpoint(monkeypatch):
    monkeypatch.setenv("VERTEX_AI_INDEX_ENDPOINT", "projects/123/locations/us/indexEndpoints/456")
    config = IngestionConfig.from_env()
    assert config.index_endpoint == "projects/123/locations/us/indexEndpoints/456"


def test_from_env_reads_deployed_index_id(monkeypatch):
    monkeypatch.setenv("VERTEX_AI_DEPLOYED_INDEX_ID", "my-deployed-index")
    config = IngestionConfig.from_env()
    assert config.deployed_index_id == "my-deployed-index"


def test_from_env_uses_default_gcs_bucket_when_absent(monkeypatch):
    monkeypatch.delenv("GCS_DOCUMENTS_BUCKET", raising=False)
    config = IngestionConfig.from_env()
    assert config.gcs_bucket == ""


def test_from_env_uses_default_raw_prefix_when_absent(monkeypatch):
    monkeypatch.delenv("GCS_RAW_PREFIX", raising=False)
    config = IngestionConfig.from_env()
    assert config.raw_prefix == "raw/"


def test_from_env_uses_default_processed_prefix_when_absent(monkeypatch):
    monkeypatch.delenv("GCS_PROCESSED_PREFIX", raising=False)
    config = IngestionConfig.from_env()
    assert config.processed_prefix == "processed/"


def test_from_env_uses_default_chunk_size_when_absent(monkeypatch):
    monkeypatch.delenv("CHUNK_SIZE", raising=False)
    config = IngestionConfig.from_env()
    assert config.chunk_size == 500


def test_from_env_uses_default_chunk_overlap_when_absent(monkeypatch):
    monkeypatch.delenv("CHUNK_OVERLAP", raising=False)
    config = IngestionConfig.from_env()
    assert config.chunk_overlap == 50


def test_from_env_uses_default_embedding_model_when_absent(monkeypatch):
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    config = IngestionConfig.from_env()
    assert config.embedding_model == "stub"


def test_from_env_uses_default_vertex_location_when_absent(monkeypatch):
    monkeypatch.delenv("VERTEX_AI_LOCATION", raising=False)
    config = IngestionConfig.from_env()
    assert config.vertex_location == "europe-west1"


def test_from_env_uses_default_index_endpoint_when_absent(monkeypatch):
    monkeypatch.delenv("VERTEX_AI_INDEX_ENDPOINT", raising=False)
    config = IngestionConfig.from_env()
    assert config.index_endpoint == ""


def test_from_env_uses_default_deployed_index_id_when_absent(monkeypatch):
    monkeypatch.delenv("VERTEX_AI_DEPLOYED_INDEX_ID", raising=False)
    config = IngestionConfig.from_env()
    assert config.deployed_index_id == ""
