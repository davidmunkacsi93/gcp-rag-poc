"""
E2E tests — verify seed data is loaded and queryable in all local services.

Prerequisites: docker compose up, load scripts executed.
Run: pytest tests/seed/test_e2e_local_data.py
"""

import os
import pytest
import psycopg
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery, storage


@pytest.fixture(scope="module")
def pg():
    conn = psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def bq():
    return bigquery.Client(
        project=os.environ["GCP_PROJECT_ID"],
        credentials=AnonymousCredentials(),
        client_options=ClientOptions(api_endpoint=os.environ["BIGQUERY_EMULATOR_HOST"]),
    )


@pytest.fixture(scope="module")
def gcs():
    return storage.Client(
        project=os.environ["GCP_PROJECT_ID"],
        credentials=AnonymousCredentials(),
        client_options=ClientOptions(api_endpoint=os.environ["GCS_EMULATOR_HOST"]),
    )


# --- PostgreSQL ---

def test_postgres_regional_metrics_has_rows(pg):
    cur = pg.cursor()
    cur.execute("SELECT COUNT(*) FROM regional.regional_metrics")
    count = cur.fetchone()[0]
    assert count > 0


def test_postgres_regional_metrics_filter_by_region_returns_rows(pg):
    cur = pg.cursor()
    cur.execute(
        "SELECT product_line, revenue_usd FROM regional.regional_metrics WHERE region = %s LIMIT 10",
        ("EMEA",),
    )
    rows = cur.fetchall()
    assert len(rows) > 0


def test_postgres_regional_metrics_risk_score_within_bounds(pg):
    cur = pg.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM regional.regional_metrics WHERE risk_score < 1 OR risk_score > 10"
    )
    invalid = cur.fetchone()[0]
    assert invalid == 0


# --- BigQuery ---

def test_bigquery_global_metrics_has_rows(bq):
    project = os.environ["GCP_PROJECT_ID"]
    result = bq.query(f"SELECT COUNT(*) AS cnt FROM `{project}.global_metrics.global_metrics`").result()
    count = next(iter(result))["cnt"]
    assert count > 0


def test_bigquery_global_metrics_filter_by_product_line_returns_rows(bq):
    project = os.environ["GCP_PROJECT_ID"]
    result = bq.query(
        f"""
        SELECT product_line, SUM(revenue_usd) AS total_revenue
        FROM `{project}.global_metrics.global_metrics`
        WHERE product_line = 'Retail Banking'
        GROUP BY product_line
        """
    ).result()
    rows = list(result)
    assert len(rows) > 0
    assert rows[0]["total_revenue"] > 0


# --- GCS ---

def test_gcs_bucket_exists(gcs):
    bucket_name = os.environ["GCS_DOCUMENTS_BUCKET"]
    bucket = gcs.lookup_bucket(bucket_name)
    assert bucket is not None


def test_gcs_documents_uploaded(gcs):
    bucket_name = os.environ["GCS_DOCUMENTS_BUCKET"]
    blobs = list(gcs.list_blobs(bucket_name, prefix="raw/"))
    assert len(blobs) > 0


def test_gcs_project_apollo_document_exists(gcs):
    bucket_name = os.environ["GCS_DOCUMENTS_BUCKET"]
    blobs = list(gcs.list_blobs(bucket_name, prefix="raw/"))
    names = [b.name for b in blobs]
    assert any("project_apollo" in name for name in names)
