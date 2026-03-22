import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

_GCP_ENV_FILE = Path(__file__).parents[4] / ".env.gcp"

_EMULATOR_VARS = (
    "FIRESTORE_EMULATOR_HOST",
    "GCS_EMULATOR_HOST",
    "BIGQUERY_EMULATOR_HOST",
    "STORAGE_EMULATOR_HOST",
)


@pytest.fixture(scope="session", autouse=True)
def _require_gcp_data(gcp_ingestion_setup):
    """Ensure real GCP data is ingested before any test in this directory."""


@pytest.fixture(scope="module", autouse=True)
def gcp_env():
    """Load .env.gcp values and unset emulator vars for each GCP E2E test module.
    All changes are rolled back after the module so other tests are unaffected."""
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
