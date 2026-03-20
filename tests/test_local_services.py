"""Smoke tests — verify all local Docker services are reachable."""

import os
import psycopg
import pytest
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery, storage


def test_postgres_reachable():
    conn = psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    cur = conn.cursor()
    cur.execute("SELECT 1")
    result = cur.fetchone()
    conn.close()
    assert result == (1,)


def test_gcs_emulator_reachable():
    client = storage.Client(
        project=os.environ["GCP_PROJECT_ID"],
        credentials=AnonymousCredentials(),
        client_options=ClientOptions(api_endpoint=os.environ["GCS_EMULATOR_HOST"]),
    )
    buckets = list(client.list_buckets())
    assert isinstance(buckets, list)


def test_bigquery_emulator_reachable():
    client = bigquery.Client(
        project=os.environ["GCP_PROJECT_ID"],
        credentials=AnonymousCredentials(),
        client_options=ClientOptions(api_endpoint=os.environ["BIGQUERY_EMULATOR_HOST"]),
    )
    datasets = list(client.list_datasets())
    assert isinstance(datasets, list)
