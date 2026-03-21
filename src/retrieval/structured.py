import logging
import os
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

import psycopg
import vertexai
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel

_BIGQUERY_SCHEMA = """
Table: `{project_id}.global_metrics.global_metrics`
Columns:
  id INTEGER, date DATE, year INTEGER, quarter STRING,
  product_line STRING, region STRING,
  revenue_usd FLOAT, cost_usd FLOAT, profit_usd FLOAT,
  profit_margin_pct FLOAT, yoy_growth_pct FLOAT,
  headcount INTEGER, customer_count INTEGER
"""

_CLOUDSQL_SCHEMA = """
Table: regional.regional_metrics
Columns:
  id INTEGER, date DATE, year INTEGER, quarter VARCHAR,
  region VARCHAR, country VARCHAR, product_line VARCHAR,
  revenue_usd NUMERIC, cost_usd NUMERIC, profit_usd NUMERIC,
  profit_margin_pct NUMERIC, market_share_pct NUMERIC, risk_score NUMERIC
"""

_SELECT_PATTERN = re.compile(r"^\s*SELECT\s", re.IGNORECASE)
_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b", re.IGNORECASE
)

_MAX_ROWS = 50


@dataclass
class StructuredResult:
    source: str
    columns: list[str]
    rows: list[tuple]
    generated_sql: str
    error: str | None = None


def _generate_sql(schema: str, nl_query: str) -> str:
    vertexai.init(
        project=os.environ["GCP_PROJECT_ID"],
        location=os.environ.get("VERTEX_AI_LOCATION", "europe-west1"),
    )
    model = GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
    prompt = (
        "You are a SQL expert. Given the schema below, write a single SQL SELECT query "
        "to answer the question. Return only the SQL with no explanation and no markdown.\n\n"
        f"Schema:\n{schema}\n\nQuestion: {nl_query}\n\nSQL:"
    )
    sql = model.generate_content(prompt).text.strip()
    return re.sub(r"^```sql\s*|^```\s*|```$", "", sql, flags=re.MULTILINE).strip()


def _is_safe_sql(sql: str) -> bool:
    return bool(_SELECT_PATTERN.match(sql)) and not bool(_DANGEROUS_PATTERN.search(sql))


def _bigquery_client() -> bigquery.Client:
    emulator_host = os.environ.get("BIGQUERY_EMULATOR_HOST")
    if emulator_host:
        return bigquery.Client(
            project=os.environ["GCP_PROJECT_ID"],
            credentials=AnonymousCredentials(),
            client_options=ClientOptions(api_endpoint=emulator_host),
        )
    return bigquery.Client(project=os.environ["GCP_PROJECT_ID"])


def _cloudsql_connection() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("CLOUD_SQL_HOST") or os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("CLOUD_SQL_PORT") or os.environ.get("POSTGRES_PORT", 5432)),
        user=os.environ.get("CLOUD_SQL_USER") or os.environ.get("POSTGRES_USER", "rag"),
        password=os.environ.get("CLOUD_SQL_PASSWORD") or os.environ.get("POSTGRES_PASSWORD", "rag"),
        dbname=os.environ.get("CLOUD_SQL_DB") or os.environ.get("POSTGRES_DB", "regional"),
    )


def query_bigquery(nl_query: str) -> StructuredResult:
    sql = ""
    try:
        schema = _BIGQUERY_SCHEMA.format(project_id=os.environ["GCP_PROJECT_ID"])
        sql = _generate_sql(schema, nl_query)
        logger.debug("BigQuery generated SQL: %s", sql)
        if not _is_safe_sql(sql):
            logger.warning("BigQuery rejected unsafe SQL: %s", sql)
            return StructuredResult(
                source="bigquery", columns=[], rows=[], generated_sql=sql,
                error=f"Rejected unsafe SQL: {sql}",
            )
        client = _bigquery_client()
        result = client.query(sql).result()
        columns = [f.name for f in result.schema]
        rows = [tuple(row) for row in result][:_MAX_ROWS]
        logger.debug("BigQuery returned %d rows", len(rows))
        return StructuredResult(source="bigquery", columns=columns, rows=rows, generated_sql=sql)
    except Exception as e:
        logger.error("BigQuery query failed. SQL: %s — Error: %s", sql, e)
        return StructuredResult(
            source="bigquery", columns=[], rows=[], generated_sql=sql, error=str(e)
        )


def query_cloudsql(nl_query: str) -> StructuredResult:
    sql = ""
    try:
        sql = _generate_sql(_CLOUDSQL_SCHEMA, nl_query)
        logger.debug("Cloud SQL generated SQL: %s", sql)
        if not _is_safe_sql(sql):
            logger.warning("Cloud SQL rejected unsafe SQL: %s", sql)
            return StructuredResult(
                source="cloudsql", columns=[], rows=[], generated_sql=sql,
                error=f"Rejected unsafe SQL: {sql}",
            )
        with _cloudsql_connection() as conn, conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchmany(_MAX_ROWS)
        logger.debug("Cloud SQL returned %d rows", len(rows))
        return StructuredResult(source="cloudsql", columns=columns, rows=rows, generated_sql=sql)
    except Exception as e:
        logger.error("Cloud SQL query failed. SQL: %s — Error: %s", sql, e)
        return StructuredResult(
            source="cloudsql", columns=[], rows=[], generated_sql=sql, error=str(e)
        )
