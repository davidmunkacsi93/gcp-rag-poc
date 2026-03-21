"""
E2E tests for the ingestion pipeline against real GCP services.

Prerequisites:
  - GCP auth: gcloud auth application-default login
  - .env sourced with GCP_PROJECT_ID, GCS_DOCUMENTS_BUCKET, FIRESTORE_* set
  - EMBEDDING_MODEL=stub to avoid Vertex AI costs
  - Emulator env vars must NOT be set

Run:
  source .env && pytest tests/ingestion/test_e2e_gcp_ingestion.py -v -m gcp
"""

import os

import pytest
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion
from src.ingestion.vector_store import MockVectorStore

RAW_PREFIX = "raw/"

_EMULATOR_VARS = ("GCS_EMULATOR_HOST", "BIGQUERY_EMULATOR_HOST", "FIRESTORE_EMULATOR_HOST", "STORAGE_EMULATOR_HOST")


@pytest.fixture(scope="module")
def gcp_config():
    saved = {var: os.environ.pop(var, None) for var in _EMULATOR_VARS}
    saved_embedding = os.environ.get("EMBEDDING_MODEL")
    os.environ["EMBEDDING_MODEL"] = "stub"
    cfg = IngestionConfig.from_env()
    yield cfg
    for var, val in saved.items():
        if val is not None:
            os.environ[var] = val
    if saved_embedding is not None:
        os.environ["EMBEDDING_MODEL"] = saved_embedding
    else:
        os.environ.pop("EMBEDDING_MODEL", None)


@pytest.fixture(scope="module")
def gcp_ingested_store(gcp_config):
    store = MockVectorStore()
    run_ingestion(gcp_config, vector_store=store)
    return store


@pytest.mark.gcp
def test_gcp_pipeline_ingests_all_documents(gcp_config, gcp_ingested_store):
    db = firestore.Client()

    ingested_docs = list(
        db.collection("documents")
        .where(filter=FieldFilter("source_key", ">=", RAW_PREFIX))
        .where(filter=FieldFilter("source_key", "<", RAW_PREFIX + "\uffff"))
        .where(filter=FieldFilter("status", "==", "ingested"))
        .stream()
    )
    assert len(ingested_docs) >= 15


@pytest.mark.gcp
def test_gcp_pipeline_is_idempotent(gcp_config):
    store1 = MockVectorStore()
    run_ingestion(gcp_config, vector_store=store1)

    store2 = MockVectorStore()
    run_ingestion(gcp_config, vector_store=store2)

    db = firestore.Client()
    all_docs = list(
        db.collection("documents")
        .where(filter=FieldFilter("source_key", ">=", RAW_PREFIX))
        .where(filter=FieldFilter("source_key", "<", RAW_PREFIX + "\uffff"))
        .stream()
    )

    seen_keys: dict[str, int] = {}
    for doc in all_docs:
        key = doc.to_dict().get("source_key", "")
        seen_keys[key] = seen_keys.get(key, 0) + 1

    duplicates = {k: v for k, v in seen_keys.items() if v > 1}
    assert not duplicates, f"Duplicate document records found: {duplicates}"
    assert len(seen_keys) >= 15


@pytest.mark.gcp
def test_gcp_chunk_lineage_is_complete(gcp_config, gcp_ingested_store):
    db = firestore.Client()

    chunk_docs = list(db.collection("chunks").limit(50).stream())
    assert chunk_docs, "No chunks found in Firestore"

    chunk = chunk_docs[0].to_dict()
    assert chunk.get("doc_id"), "chunk.doc_id is missing or empty"
    assert chunk.get("text"), "chunk.text is missing or empty"
    assert chunk.get("section"), "chunk.section is missing or empty"
    assert chunk.get("chunk_id"), "chunk.chunk_id is missing or empty"

    doc_id = chunk["doc_id"]
    doc_ref = db.collection("documents").document(doc_id).get()
    assert doc_ref.exists, f"Parent document {doc_id} not found in Firestore"

    doc_data = doc_ref.to_dict()
    source_key = doc_data.get("source_key", "")
    assert source_key.startswith(RAW_PREFIX), (
        f"source_key '{source_key}' does not start with '{RAW_PREFIX}'"
    )
