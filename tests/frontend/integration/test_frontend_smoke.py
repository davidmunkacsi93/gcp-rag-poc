"""
Smoke test for the Streamlit frontend.

Run:
  pytest tests/deployment/test_frontend_smoke.py -v -m integration
"""

import socket
import subprocess
import sys
import time

import httpx
import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.mark.integration
def test_frontend_starts_and_serves_http():
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            "src/frontend/app.py",
            f"--server.port={port}",
            "--server.address=0.0.0.0",
            "--server.headless=true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        deadline = time.monotonic() + 10
        last_exc: Exception | None = None

        while time.monotonic() < deadline:
            assert proc.poll() is None, "Streamlit process exited prematurely"
            try:
                response = httpx.get(f"http://localhost:{port}", timeout=1.0)
                assert response.status_code == 200
                return
            except Exception as exc:
                last_exc = exc
                time.sleep(0.5)

        raise AssertionError(
            f"Frontend did not respond within 10 seconds. Last error: {last_exc}"
        )
    finally:
        proc.terminate()
        proc.wait()
