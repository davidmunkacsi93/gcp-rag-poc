"""
Session-scoped fixtures for the self-contained GCP E2E test suite.

Setup:   ingest two controlled test documents into real GCP services
         (Vertex AI embedder, Vertex AI Vector Search, Firestore).
Teardown: remove exactly what was created — Firestore records and
          vector store datapoints — leaving the environment unchanged.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import dotenv_values
from google.cloud import aiplatform, firestore

from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion

_GCP_ENV_FILE = Path(__file__).parents[2] / ".env.gcp"

_EMULATOR_VARS = (
    "FIRESTORE_EMULATOR_HOST",
    "GCS_EMULATOR_HOST",
    "BIGQUERY_EMULATOR_HOST",
    "STORAGE_EMULATOR_HOST",
)

# Small, controlled documents with unique identifiers so queries
# target these specifically and are not drowned out by production data.
_TEST_DOCS = {
    "raw/e2e_test_remediation_project_zenith.md": """\
# Remediation Guidance: Project Zenith

## Overview

Project Zenith requires immediate remediation of supply chain vulnerabilities
identified in the Q3 2024 operational review. Three critical action items have
been escalated to the executive committee for resolution before year-end.

## Action Plan

1. Restructure supplier contracts to reduce single-source dependencies in EMEA.
2. Implement real-time inventory monitoring and automated alert thresholds.
3. Establish a regional backup supplier network across key EMEA markets.

Each action has been assigned a responsible owner and a target completion date
tracked through the programme management office.
""",
    "raw/e2e_test_risk_assessment_project_zenith.md": """\
# Risk Assessment: Project Zenith Initiative

## Executive Summary

The Project Zenith Initiative faces three material risks in the current
operating environment: regulatory non-compliance, liquidity constraints,
and technology integration failures requiring executive attention.

## Risk Register

- **Regulatory**: Pending Basel IV capital requirements create a projected
  12% capital shortfall that must be addressed by Q1 2025.
- **Liquidity**: Working capital ratio is below the industry benchmark,
  requiring a £50m short-term credit facility to be secured.
- **Technology**: Legacy system migration is delayed by six months due to
  vendor resourcing constraints, increasing operational risk exposure.
""",
}


@pytest.fixture(scope="session", autouse=True)
def gcp_env():
    """Load .env.gcp and unset all emulator vars for the duration of the session."""
    gcp_values = {k: v for k, v in dotenv_values(_GCP_ENV_FILE).items() if v is not None}
    all_keys = set(gcp_values) | set(_EMULATOR_VARS)
    saved = {k: os.environ.get(k) for k in all_keys}

    for k, v in gcp_values.items():
        os.environ[k] = v
    for var in _EMULATOR_VARS:
        os.environ.pop(var, None)

    yield

    for k, orig in saved.items():
        if orig is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig


@pytest.fixture(scope="session")
def pipeline_data(gcp_env):
    """
    Ingest the test documents into real GCP services and yield metadata.
    On teardown, remove exactly the Firestore records and vector datapoints
    created during this session.
    """
    db = firestore.Client()

    existing_doc_ids = {doc.id for doc in db.collection("documents").stream()}
    existing_chunk_ids = {doc.id for doc in db.collection("chunks").stream()}

    config = IngestionConfig.from_env()
    doc_list = [
        {"name": k, "size": len(v), "updated": None}
        for k, v in _TEST_DOCS.items()
    ]

    with (
        patch("src.ingestion.pipeline.list_raw_documents", return_value=doc_list),
        patch("src.ingestion.pipeline.read_document", side_effect=lambda _cfg, k: _TEST_DOCS[k]),
    ):
        run_ingestion(config)

    new_chunk_docs = [
        doc for doc in db.collection("chunks").stream()
        if doc.id not in existing_chunk_ids
    ]
    new_chunk_firestore_ids = [doc.id for doc in new_chunk_docs]
    new_chunk_vector_ids = [
        doc.to_dict().get("chunk_id") for doc in new_chunk_docs
        if doc.to_dict().get("chunk_id")
    ]
    new_doc_ids = [
        doc.id for doc in db.collection("documents").stream()
        if doc.id not in existing_doc_ids
    ]

    yield {
        "doc_source_keys": list(_TEST_DOCS.keys()),
        "chunk_vector_ids": new_chunk_vector_ids,
    }

    # Teardown — restore environment and remove only what we created
    for k, v in dotenv_values(_GCP_ENV_FILE).items():
        if v is not None:
            os.environ[k] = v
    for var in _EMULATOR_VARS:
        os.environ.pop(var, None)

    if new_chunk_vector_ids:
        aiplatform.init(
            project=os.environ["GCP_PROJECT_ID"],
            location=os.environ["VERTEX_AI_LOCATION"],
        )
        index = aiplatform.MatchingEngineIndex(index_name=os.environ["VERTEX_AI_INDEX_ID"])
        index.remove_datapoints(datapoint_ids=new_chunk_vector_ids)

    db2 = firestore.Client()
    for doc_id in new_doc_ids:
        db2.collection("documents").document(doc_id).delete()
    for chunk_firestore_id in new_chunk_firestore_ids:
        db2.collection("chunks").document(chunk_firestore_id).delete()
