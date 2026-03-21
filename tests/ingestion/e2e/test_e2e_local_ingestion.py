"""
Integration tests for the full ingestion pipeline against local Docker environment.

Prerequisites:
  - docker compose up (fake-gcs-server on :4443, Firestore emulator on :8090)
  - Seed documents loaded: python scripts/seed/load_gcs_local.py

Run:
  pytest tests/ingestion/e2e/test_e2e_local_ingestion.py -v -m integration
"""

import os

import pytest
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion
from src.ingestion.vector_store import MockVectorStore

RAW_PREFIX = "raw/"


@pytest.fixture(scope="module")
def config():
    return IngestionConfig(
        gcs_bucket=os.getenv("GCS_DOCUMENTS_BUCKET", "rag-poc-documents-dev"),
        raw_prefix=RAW_PREFIX,
        processed_prefix="processed/",
        chunk_size=500,
        chunk_overlap=50,
        embedding_model="stub",
        vertex_location="europe-west1",
        index_id="",
        index_endpoint="",
        deployed_index_id="",
    )


@pytest.fixture(scope="module")
def ingested_store(config):
    store = MockVectorStore()
    run_ingestion(config, vector_store=store)
    return store


@pytest.mark.integration
def test_all_seed_documents_are_ingested(config, ingested_store):
    db = firestore.Client()

    ingested_docs = list(
        db.collection("documents")
        .where(filter=FieldFilter("source_key", ">=", RAW_PREFIX))
        .where(filter=FieldFilter("source_key", "<", RAW_PREFIX + "\uffff"))
        .where(filter=FieldFilter("status", "==", "ingested"))
        .stream()
    )
    assert len(ingested_docs) >= 15

    chunk_docs = list(
        db.collection("chunks")
        .stream()
    )
    doc_ids_from_ingested = {d.id for d in ingested_docs}
    chunks_for_seed = [
        c for c in chunk_docs if c.to_dict().get("doc_id") in doc_ids_from_ingested
    ]
    assert 50 <= len(chunks_for_seed) <= 500


@pytest.mark.integration
def test_pipeline_is_idempotent(config):
    store1 = MockVectorStore()
    run_ingestion(config, vector_store=store1)

    store2 = MockVectorStore()
    run_ingestion(config, vector_store=store2)

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


@pytest.mark.integration
def test_each_chunk_has_source_lineage(config, ingested_store):
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


@pytest.mark.integration
def test_vector_store_receives_embeddings_for_all_chunks(config, ingested_store):
    assert len(ingested_store.upserted) > 0

    for datapoint in ingested_store.upserted:
        assert datapoint.get("datapoint_id"), "datapoint missing datapoint_id"
        vector = datapoint.get("feature_vector", [])
        assert len(vector) == 768, f"Expected 768-dim vector, got {len(vector)}"
        assert datapoint.get("restricts"), "datapoint missing restricts"
