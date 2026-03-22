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
    """Session-scoped fixture: clear Firestore, run real ingestion, clean up after.

    Uses the real VectorStore (no MockVectorStore) so Firestore and Vector Search
    are always in sync. Called explicitly by GCP test conftest files via a
    session-scoped autouse fixture — never runs for local/unit tests.
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

    # Clear Firestore
    db = firestore.Client()
    for collection in ("documents", "chunks"):
        for doc in db.collection(collection).stream():
            doc.reference.delete()

    # Run real ingestion (vector_store=None → creates real VectorStore)
    config = IngestionConfig.from_env()
    run_ingestion(config)

    # Collect chunk IDs for teardown cleanup
    chunk_ids = [doc.id for doc in db.collection("chunks").stream()]

    # Restore env — per-test gcp_env fixtures handle test-level env
    for k, orig in saved.items():
        if orig is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig

    yield

    # --- teardown: activate GCP env again ---
    for k, v in gcp_values.items():
        os.environ[k] = v
    for var in _EMULATOR_VARS:
        os.environ.pop(var, None)

    # Remove datapoints from Vector Search
    aiplatform.init(
        project=os.environ["GCP_PROJECT_ID"],
        location=os.environ["VERTEX_AI_LOCATION"],
    )
    index = aiplatform.MatchingEngineIndex(index_name=os.environ["VERTEX_AI_INDEX_ID"])
    if chunk_ids:
        index.remove_datapoints(datapoint_ids=chunk_ids)

    # Clear Firestore
    db = firestore.Client()
    for collection in ("documents", "chunks"):
        for doc in db.collection(collection).stream():
            doc.reference.delete()

    # Restore env
    for k, orig in saved.items():
        if orig is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig
