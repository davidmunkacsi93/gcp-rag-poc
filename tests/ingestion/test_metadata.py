"""Tests for the MetadataStore module — runs against the Firestore emulator."""

import uuid

import pytest
from google.cloud.firestore_v1.base_query import FieldFilter

from src.ingestion.metadata import MetadataStore


def _unique_id() -> str:
    return uuid.uuid4().hex[:12]


@pytest.fixture
def store():
    return MetadataStore()


@pytest.mark.integration
def test_is_ingested_returns_false_when_document_does_not_exist(store):
    assert store.is_ingested(f"raw/nonexistent_{_unique_id()}.md") is False


@pytest.mark.integration
def test_is_ingested_returns_true_after_create_and_mark_ingested(store):
    doc_id = _unique_id()
    source_key = f"raw/strategy_memo_{doc_id}.md"
    store.create_document_record(doc_id, source_key, "Test Title", "strategy_memo")
    store.mark_ingested(doc_id, chunk_count=3)
    assert store.is_ingested(source_key) is True


@pytest.mark.integration
def test_create_document_record_writes_document_with_pending_status(store):
    doc_id = _unique_id()
    source_key = f"raw/strategy_memo_{doc_id}.md"
    store.create_document_record(doc_id, source_key, "Pending Title", "strategy_memo")

    from google.cloud import firestore
    db = firestore.Client()
    snapshot = db.collection("documents").document(doc_id).get()
    assert snapshot.exists
    assert snapshot.get("status") == "pending"


@pytest.mark.integration
def test_mark_ingested_updates_status_and_sets_chunk_count(store):
    doc_id = _unique_id()
    source_key = f"raw/strategy_memo_{doc_id}.md"
    store.create_document_record(doc_id, source_key, "Ingested Title", "strategy_memo")
    store.mark_ingested(doc_id, chunk_count=7)

    from google.cloud import firestore
    db = firestore.Client()
    snapshot = db.collection("documents").document(doc_id).get()
    assert snapshot.get("status") == "ingested"
    assert snapshot.get("chunk_count") == 7


@pytest.mark.integration
def test_mark_error_updates_status_and_sets_error_message(store):
    doc_id = _unique_id()
    source_key = f"raw/risk_assessment_{doc_id}.md"
    store.create_document_record(doc_id, source_key, "Error Title", "risk_assessment")
    store.mark_error(doc_id, "Something went wrong")

    from google.cloud import firestore
    db = firestore.Client()
    snapshot = db.collection("documents").document(doc_id).get()
    assert snapshot.get("status") == "error"
    assert snapshot.get("error_message") == "Something went wrong"


@pytest.mark.integration
def test_write_chunks_writes_correct_number_of_chunk_documents(store):
    doc_id = _unique_id()
    source_key = f"raw/remediation_{doc_id}.md"
    store.create_document_record(doc_id, source_key, "Chunk Count Title", "remediation")

    chunks = [
        {"chunk_id": f"{doc_id}_0", "text": "First chunk.", "section": "Intro", "chunk_index": 0, "token_count": 10},
        {"chunk_id": f"{doc_id}_1", "text": "Second chunk.", "section": "Intro", "chunk_index": 1, "token_count": 10},
        {"chunk_id": f"{doc_id}_2", "text": "Third chunk.", "section": "Body", "chunk_index": 2, "token_count": 10},
    ]
    store.write_chunks(doc_id, chunks)

    from google.cloud import firestore
    db = firestore.Client()
    results = list(db.collection("chunks").where(filter=FieldFilter("doc_id", "==", doc_id)).stream())
    assert len(results) == 3


@pytest.mark.integration
def test_write_chunks_each_chunk_document_has_matching_doc_id(store):
    doc_id = _unique_id()
    source_key = f"raw/regulatory_{doc_id}.md"
    store.create_document_record(doc_id, source_key, "Doc ID Check Title", "regulatory")

    chunks = [
        {"chunk_id": f"{doc_id}_0", "text": "Alpha chunk.", "section": "Overview", "chunk_index": 0, "token_count": 5},
        {"chunk_id": f"{doc_id}_1", "text": "Beta chunk.", "section": "Overview", "chunk_index": 1, "token_count": 5},
    ]
    store.write_chunks(doc_id, chunks)

    from google.cloud import firestore
    db = firestore.Client()
    results = list(db.collection("chunks").where(filter=FieldFilter("doc_id", "==", doc_id)).stream())
    for result in results:
        assert result.get("doc_id") == doc_id
