import os

import pytest

_EMULATOR_VARS = (
    "FIRESTORE_EMULATOR_HOST",
    "GCS_EMULATOR_HOST",
    "BIGQUERY_EMULATOR_HOST",
    "STORAGE_EMULATOR_HOST",
)


@pytest.fixture(autouse=True, scope="session")
def unset_emulator_env_vars():
    """Remove emulator env vars so GCP E2E tests hit real GCP services."""
    for var in _EMULATOR_VARS:
        os.environ.pop(var, None)
