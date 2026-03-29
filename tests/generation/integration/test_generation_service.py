"""
In-process HTTP wrapper tests for the generation service.

Run:
  pytest tests/deployment/test_generation_service.py -v -m integration
"""

import asyncio
import os

import httpx
import pytest


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch):
    monkeypatch.setenv("GENERATION_STUB", "true")
    monkeypatch.setenv("EMBEDDING_MODEL", "stub")


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def client():
    from src.generation.service import app

    async def _make():
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )

    return _run(_make())


@pytest.mark.integration
def test_health_returns_healthy(client):
    async def _go():
        async with client:
            return await client.get("/health")

    response = _run(_go())
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.integration
def test_generate_returns_200(client):
    async def _go():
        async with client:
            return await client.post("/generate", json={"query": "What is the revenue for EMEA?"})

    response = _run(_go())
    assert response.status_code == 200


@pytest.mark.integration
def test_generate_response_shape(client):
    async def _go():
        async with client:
            return await client.post("/generate", json={"query": "What is the revenue for EMEA?"})

    data = _run(_go()).json()
    assert isinstance(data["answer"], str) and data["answer"]
    assert isinstance(data["citations"], list)
    assert isinstance(data["model"], str) and data["model"]
    assert isinstance(data["prompt_tokens"], int)
