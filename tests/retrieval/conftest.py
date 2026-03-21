import os

import psycopg
import pytest
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery


@pytest.fixture(scope="session", autouse=True)
def require_postgres():
    """Fail fast if local PostgreSQL is unreachable."""
    if os.environ.get("CLOUD_SQL_HOST"):
        return  # GCP mode — connection handled by structured retriever directly
    try:
        conn = psycopg.connect(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ["POSTGRES_PORT"]),
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            dbname=os.environ["POSTGRES_DB"],
        )
        conn.close()
    except Exception as e:
        pytest.fail(
            f"Local PostgreSQL is unreachable — is Docker running? "
            f"Run: docker compose -f docker/docker-compose.yml up -d\n{e}"
        )


@pytest.fixture(scope="session", autouse=True)
def require_bigquery():
    """Fail fast if local BigQuery emulator is unreachable."""
    if not os.environ.get("BIGQUERY_EMULATOR_HOST"):
        return  # GCP mode — real BigQuery, no connectivity pre-check needed
    try:
        client = bigquery.Client(
            project=os.environ["GCP_PROJECT_ID"],
            credentials=AnonymousCredentials(),
            client_options=ClientOptions(
                api_endpoint=os.environ["BIGQUERY_EMULATOR_HOST"]
            ),
        )
        list(client.list_datasets())
    except Exception as e:
        pytest.fail(
            f"BigQuery emulator is unreachable — is Docker running? "
            f"Run: docker compose -f docker/docker-compose.yml up -d\n{e}"
        )
