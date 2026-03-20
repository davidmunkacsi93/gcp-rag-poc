"""
E2E tests — verify seed data is loaded and queryable in GCP services.

Prerequisites:
  - GCP auth: gcloud auth application-default login
  - .env sourced with GCP_PROJECT_ID, CLOUD_SQL_*, GCS_BUCKET set
  - BIGQUERY_EMULATOR_HOST must NOT be set (unset before running)

Run:
  source .env && unset BIGQUERY_EMULATOR_HOST && pytest tests/seed/test_e2e_gcp_data.py -v -m gcp
"""

import os
import pytest
import psycopg
from google.cloud import bigquery, storage


@pytest.fixture(scope="module", autouse=True)
def unset_bigquery_emulator():
    """Ensure BigQuery calls go to GCP, not the local emulator."""
    original = os.environ.pop("BIGQUERY_EMULATOR_HOST", None)
    yield
    if original:
        os.environ["BIGQUERY_EMULATOR_HOST"] = original


@pytest.fixture(scope="module")
def pg():
    conn = psycopg.connect(
        host=os.environ["CLOUD_SQL_HOST"],
        port=int(os.environ.get("CLOUD_SQL_PORT", 5432)),
        user=os.environ["CLOUD_SQL_USER"],
        password=os.environ["CLOUD_SQL_PASSWORD"],
        dbname=os.environ["CLOUD_SQL_DB"],
    )
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def bq():
    return bigquery.Client(project=os.environ["GCP_PROJECT_ID"])


@pytest.fixture(scope="module")
def gcs():
    return storage.Client(project=os.environ["GCP_PROJECT_ID"])


# --- Cloud SQL ---

@pytest.mark.gcp
def test_cloud_sql_regional_metrics_has_rows(pg):
    cur = pg.cursor()
    cur.execute("SELECT COUNT(*) FROM regional.regional_metrics")
    count = cur.fetchone()[0]
    assert count > 0


@pytest.mark.gcp
def test_cloud_sql_regional_metrics_filter_by_region_returns_rows(pg):
    cur = pg.cursor()
    cur.execute(
        "SELECT product_line, revenue_usd FROM regional.regional_metrics WHERE region = %s LIMIT 10",
        ("EMEA",),
    )
    rows = cur.fetchall()
    assert len(rows) > 0


@pytest.mark.gcp
def test_cloud_sql_regional_metrics_risk_score_within_bounds(pg):
    cur = pg.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM regional.regional_metrics WHERE risk_score < 1 OR risk_score > 10"
    )
    invalid = cur.fetchone()[0]
    assert invalid == 0


# --- BigQuery ---

@pytest.mark.gcp
def test_bigquery_global_metrics_has_rows(bq):
    project = os.environ["GCP_PROJECT_ID"]
    result = bq.query(
        f"SELECT COUNT(*) AS cnt FROM `{project}.global_metrics.global_metrics`"
    ).result()
    count = next(iter(result))["cnt"]
    assert count > 0


@pytest.mark.gcp
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

@pytest.mark.gcp
def test_gcs_bucket_exists(gcs):
    bucket_name = os.environ["GCS_BUCKET"]
    bucket = gcs.lookup_bucket(bucket_name)
    assert bucket is not None


@pytest.mark.gcp
def test_gcs_documents_uploaded(gcs):
    bucket_name = os.environ["GCS_BUCKET"]
    blobs = list(gcs.list_blobs(bucket_name, prefix="raw/"))
    assert len(blobs) > 0


@pytest.mark.gcp
def test_gcs_project_apollo_document_exists(gcs):
    bucket_name = os.environ["GCS_BUCKET"]
    blobs = list(gcs.list_blobs(bucket_name, prefix="raw/"))
    names = [b.name for b in blobs]
    assert any("project_apollo" in name for name in names)
