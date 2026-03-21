"""Tests for the ingestion pipeline — runs against the Firestore emulator."""

import uuid

import pytest
from google.cloud.firestore_v1.base_query import FieldFilter

from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion
from src.ingestion.vector_store import MockVectorStore


def _unique_key(prefix: str) -> str:
    return f"raw/{prefix}_{uuid.uuid4().hex[:10]}.md"


DOC_A_TEXT = """\
# Strategy Memo Alpha

## Background

This section provides the background context for the strategy memo.
It contains multiple sentences that will be chunked during ingestion.
Each sentence adds more words to ensure the body is long enough.

## Recommendations

These are the recommendations based on the analysis performed.
The team should consider the following points carefully.
Further review may be required before implementation.
"""

DOC_B_TEXT = """\
# Risk Assessment Beta

## Risk Overview

This document outlines the identified risks for the current quarter.
Each risk has been assessed and assigned a severity level.
Mitigation strategies have been proposed for each item.

## Mitigation Plan

The mitigation plan details specific actions to address the risks.
Owners have been assigned to each action item.
Progress will be tracked on a weekly basis.
"""


@pytest.fixture
def base_config(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "stub")
    return IngestionConfig(
        gcs_bucket="rag-poc-documents-dev",
        raw_prefix="raw/",
        processed_prefix="processed/",
        chunk_size=100,
        chunk_overlap=20,
        embedding_model="stub",
        vertex_location="europe-west1",
        index_id="",
        index_endpoint="",
        deployed_index_id="",
    )


def _patch_reader(monkeypatch, docs: list[dict], contents: dict[str, str]) -> None:
    monkeypatch.setattr(
        "src.ingestion.pipeline.list_raw_documents",
        lambda config: docs,
    )
    monkeypatch.setattr(
        "src.ingestion.pipeline.read_document",
        lambda config, key: contents[key],
    )


@pytest.mark.integration
def test_run_ingestion_calls_upsert_once_per_document(monkeypatch, base_config):
    doc_a_key = _unique_key("strategy_memo")
    doc_b_key = _unique_key("risk_assessment")
    docs = [
        {"name": doc_a_key, "size": len(DOC_A_TEXT), "updated": None},
        {"name": doc_b_key, "size": len(DOC_B_TEXT), "updated": None},
    ]
    contents = {doc_a_key: DOC_A_TEXT, doc_b_key: DOC_B_TEXT}
    _patch_reader(monkeypatch, docs, contents)

    store = MockVectorStore()
    run_ingestion(base_config, vector_store=store)

    from google.cloud import firestore
    db = firestore.Client()
    docs_a = list(db.collection("documents").where(filter=FieldFilter("source_key", "==", doc_a_key)).stream())
    docs_b = list(db.collection("documents").where(filter=FieldFilter("source_key", "==", doc_b_key)).stream())

    assert len(docs_a) == 1
    assert len(docs_b) == 1
    assert len(store.upserted) > 0


@pytest.mark.integration
def test_run_ingestion_skips_already_ingested_document(monkeypatch, base_config):
    normal_key = _unique_key("strategy_memo")
    already_ingested_key = _unique_key("strategy_memo")

    docs = [
        {"name": normal_key, "size": len(DOC_A_TEXT), "updated": None},
        {"name": already_ingested_key, "size": len(DOC_A_TEXT), "updated": None},
    ]
    contents = {normal_key: DOC_A_TEXT, already_ingested_key: DOC_A_TEXT}
    _patch_reader(monkeypatch, docs, contents)

    from src.ingestion.metadata import MetadataStore
    metadata = MetadataStore()
    pre_doc_id = uuid.uuid4().hex
    metadata.create_document_record(pre_doc_id, already_ingested_key, "Pre-ingested", "strategy_memo")
    metadata.mark_ingested(pre_doc_id, chunk_count=1)

    store = MockVectorStore()
    run_ingestion(base_config, vector_store=store)

    from google.cloud import firestore
    db = firestore.Client()
    ingested_records = list(
        db.collection("documents")
        .where(filter=FieldFilter("source_key", "==", already_ingested_key))
        .where(filter=FieldFilter("status", "==", "ingested"))
        .stream()
    )
    assert len(ingested_records) >= 1

    chunk_records_for_skipped = list(
        db.collection("chunks").where(filter=FieldFilter("doc_id", "==", pre_doc_id)).stream()
    )
    assert chunk_records_for_skipped == []


@pytest.mark.integration
def test_run_ingestion_marks_document_as_ingested_after_success(monkeypatch, base_config):
    unique_key = _unique_key("strategy_memo")
    _patch_reader(
        monkeypatch,
        docs=[{"name": unique_key, "size": len(DOC_A_TEXT), "updated": None}],
        contents={unique_key: DOC_A_TEXT},
    )
    store = MockVectorStore()
    run_ingestion(base_config, vector_store=store)

    from google.cloud import firestore
    db = firestore.Client()
    results = list(
        db.collection("documents")
        .where(filter=FieldFilter("source_key", "==", unique_key))
        .where(filter=FieldFilter("status", "==", "ingested"))
        .stream()
    )
    assert len(results) == 1


@pytest.mark.integration
def test_run_ingestion_marks_document_as_error_and_continues_when_exception_occurs(
    monkeypatch, base_config
):
    error_key = _unique_key("risk_assessment")
    ok_key = _unique_key("strategy_memo")

    _patch_reader(
        monkeypatch,
        docs=[
            {"name": error_key, "size": len(DOC_A_TEXT), "updated": None},
            {"name": ok_key, "size": len(DOC_B_TEXT), "updated": None},
        ],
        contents={error_key: DOC_A_TEXT, ok_key: DOC_B_TEXT},
    )

    call_count = {"n": 0}

    class ErrorOnFirstUpsertStore:
        def __init__(self):
            self.upserted: list[dict] = []

        def upsert(self, datapoints: list[dict]) -> None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("simulated upsert failure")
            self.upserted.extend(datapoints)

    store = ErrorOnFirstUpsertStore()
    run_ingestion(base_config, vector_store=store)

    from google.cloud import firestore
    db = firestore.Client()

    error_results = list(
        db.collection("documents")
        .where(filter=FieldFilter("source_key", "==", error_key))
        .where(filter=FieldFilter("status", "==", "error"))
        .stream()
    )
    assert len(error_results) == 1

    ok_results = list(
        db.collection("documents")
        .where(filter=FieldFilter("source_key", "==", ok_key))
        .where(filter=FieldFilter("status", "==", "ingested"))
        .stream()
    )
    assert len(ok_results) == 1


@pytest.mark.integration
def test_run_ingestion_produces_chunk_records_in_firestore_for_each_processed_document(
    monkeypatch, base_config
):
    doc_a_key = _unique_key("strategy_memo")
    doc_b_key = _unique_key("risk_assessment")

    _patch_reader(
        monkeypatch,
        docs=[
            {"name": doc_a_key, "size": len(DOC_A_TEXT), "updated": None},
            {"name": doc_b_key, "size": len(DOC_B_TEXT), "updated": None},
        ],
        contents={doc_a_key: DOC_A_TEXT, doc_b_key: DOC_B_TEXT},
    )
    store = MockVectorStore()
    run_ingestion(base_config, vector_store=store)

    from google.cloud import firestore
    db = firestore.Client()

    for key in (doc_a_key, doc_b_key):
        doc_records = list(
            db.collection("documents").where(filter=FieldFilter("source_key", "==", key)).stream()
        )
        assert len(doc_records) == 1
        doc_id = doc_records[0].id

        chunk_records = list(
            db.collection("chunks").where(filter=FieldFilter("doc_id", "==", doc_id)).stream()
        )
        assert len(chunk_records) > 0
