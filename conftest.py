from dotenv import load_dotenv, dotenv_values
from pathlib import Path

load_dotenv(override=True)

import os
import pytest

_GCP_ENV_FILE = Path(__file__).parent / ".env.gcp"

_EMULATOR_VARS = (
    "FIRESTORE_EMULATOR_HOST",
    "GCS_EMULATOR_HOST",
    "BIGQUERY_EMULATOR_HOST",
    "STORAGE_EMULATOR_HOST",
)


@pytest.fixture(scope="session")
def gcp_ingestion_setup():
    """Session-scoped fixture: run real ingestion, clean up only what was added.

    Uses the real VectorStore (no MockVectorStore) so Firestore and Vector Search
    are always in sync. Pre-existing documents are never touched — only IDs created
    in this session are removed on teardown, leaving the system in the state it was
    before the test run. Never runs for local/unit tests.
    """
    from google.cloud import aiplatform, firestore
    from src.ingestion.config import IngestionConfig
    from src.ingestion.pipeline import run_ingestion

    gcp_values = {k: v for k, v in dotenv_values(_GCP_ENV_FILE).items() if v is not None}
    all_keys = set(gcp_values) | set(_EMULATOR_VARS)
    saved = {k: os.environ.get(k) for k in all_keys}

    # --- setup: activate GCP env ---
    for k, v in gcp_values.items():
        os.environ[k] = v
    for var in _EMULATOR_VARS:
        os.environ.pop(var, None)

    db = firestore.Client()

    # Snapshot pre-existing IDs so teardown only removes what this session adds
    existing_doc_ids = {doc.id for doc in db.collection("documents").stream()}
    existing_chunk_ids = {doc.id for doc in db.collection("chunks").stream()}

    # Run real ingestion (vector_store=None → creates real VectorStore)
    config = IngestionConfig.from_env()
    run_ingestion(config)

    # Collect only the IDs created in this session
    new_doc_ids = [
        doc.id for doc in db.collection("documents").stream()
        if doc.id not in existing_doc_ids
    ]
    new_chunk_ids = [
        doc.id for doc in db.collection("chunks").stream()
        if doc.id not in existing_chunk_ids
    ]

    # Restore env — per-test gcp_env fixtures handle test-level env
    for k, orig in saved.items():
        if orig is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig

    yield

    # --- teardown: remove only what this session created ---
    for k, v in gcp_values.items():
        os.environ[k] = v
    for var in _EMULATOR_VARS:
        os.environ.pop(var, None)

    if new_chunk_ids:
        aiplatform.init(
            project=os.environ["GCP_PROJECT_ID"],
            location=os.environ["VERTEX_AI_LOCATION"],
        )
        index = aiplatform.MatchingEngineIndex(index_name=os.environ["VERTEX_AI_INDEX_ID"])
        index.remove_datapoints(datapoint_ids=new_chunk_ids)

    db = firestore.Client()
    for doc_id in new_doc_ids:
        db.collection("documents").document(doc_id).delete()
    for chunk_id in new_chunk_ids:
        db.collection("chunks").document(chunk_id).delete()

    # Restore env
    for k, orig in saved.items():
        if orig is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig
