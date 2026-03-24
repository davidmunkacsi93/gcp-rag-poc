import os
from unittest.mock import patch

import pytest
from google.cloud import firestore

from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import run_ingestion
from src.retrieval.vector_store import StubVectorSearchClient

_DOCS = {
    "raw/risk_assessment_test.md": """\
# Risk Assessment: Project Alpha

## Executive Summary

This risk assessment covers the key risks identified for Project Alpha in Q3 2024.
The project faces significant market exposure and operational challenges that require
immediate attention and mitigation planning by the risk management team.

## Risk Factors

The primary risk factors include regulatory compliance gaps and market volatility.
Each risk has been assigned a severity level and a designated mitigation owner.
""",
    "raw/remediation_guidance_test.md": """\
# Remediation Guidance: Retail Banking

## Overview

This document provides remediation guidance for the Retail Banking product line.
Following recent performance reviews, specific corrective actions are required
to address identified gaps in customer acquisition and cost management.

## Action Plan

The remediation plan focuses on improving customer acquisition and cost efficiency.
Each action item has been assigned to a specific team with a target completion date.
""",
}


@pytest.fixture(scope="module")
def ingested_stub():
    """Populate Firestore emulator and StubVectorSearchClient with inline test documents."""
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        db = firestore.Client()
        for collection in ("documents", "chunks"):
            for doc in db.collection(collection).stream():
                doc.reference.delete()

    stub = StubVectorSearchClient()
    config = IngestionConfig(
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
    doc_list = [{"name": k, "size": len(v), "updated": None} for k, v in _DOCS.items()]

    with (
        patch("src.ingestion.pipeline.list_raw_documents", return_value=doc_list),
        patch("src.ingestion.pipeline.read_document", side_effect=lambda c, k: _DOCS[k]),
    ):
        run_ingestion(config, vector_store=stub)

    return stub
