"""
Cloud Run smoke tests — require deployed services.

URLs are resolved from `terraform output` automatically.
Env vars (RETRIEVAL_SERVICE_URL, GENERATION_SERVICE_URL, FRONTEND_URL) are
used as fallback if Terraform is not available.

Authentication:
  Retrieval and generation services are private (no allUsers invoker).
  An identity token is obtained via gcloud CLI. Ensure you are logged in:

    gcloud auth login

Run:
  pytest tests/e2e/test_e2e_cloud_run.py -v -m gcp
"""

import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest
from google.auth.transport.requests import Request
from google.oauth2 import id_token  # works with SA creds; gcloud CLI used as fallback

_TERRAFORM_DIR = Path(__file__).parents[2] / "terraform"


def _terraform_outputs() -> dict:
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=_TERRAFORM_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {k: v["value"] for k, v in json.loads(result.stdout).items()}
    except Exception:
        pass
    return {}


@pytest.fixture(scope="module")
def tf_outputs() -> dict:
    return _terraform_outputs()


@pytest.fixture(scope="module")
def retrieval_url(tf_outputs) -> str:
    url = tf_outputs.get("retrieval_service_url") or os.environ.get("RETRIEVAL_SERVICE_URL", "")
    if not url:
        pytest.skip("retrieval_service_url not available from terraform output or RETRIEVAL_SERVICE_URL")
    return url


@pytest.fixture(scope="module")
def generation_url(tf_outputs) -> str:
    url = tf_outputs.get("generation_service_url") or os.environ.get("GENERATION_SERVICE_URL", "")
    if not url:
        pytest.skip("generation_service_url not available from terraform output or GENERATION_SERVICE_URL")
    return url


@pytest.fixture(scope="module")
def frontend_url(tf_outputs) -> str:
    url = tf_outputs.get("frontend_url") or os.environ.get("FRONTEND_URL", "")
    if not url:
        pytest.skip("frontend_url not available from terraform output or FRONTEND_URL")
    return url


def _auth_headers(audience: str) -> dict:
    try:
        token = id_token.fetch_id_token(Request(), audience)
    except Exception:
        # fetch_id_token requires service account credentials.
        # For user accounts (gcloud auth login), fall back to gcloud CLI
        # without --audiences (which only works with service accounts).
        result = subprocess.run(
            ["gcloud", "auth", "print-identity-token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            pytest.skip("No GCP credentials available — run: gcloud auth login")
        token = result.stdout.strip()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.gcp
def test_retrieval_health(retrieval_url):
    response = httpx.get(f"{retrieval_url}/health", headers=_auth_headers(retrieval_url), timeout=10.0)
    assert response.status_code == 200


@pytest.mark.gcp
def test_generation_health(generation_url):
    response = httpx.get(f"{generation_url}/health", headers=_auth_headers(generation_url), timeout=10.0)
    assert response.status_code == 200


@pytest.mark.gcp
def test_frontend_serves_http(frontend_url):
    response = httpx.get(frontend_url, timeout=10.0)
    assert response.status_code == 200
