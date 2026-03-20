# Data Sources — Reference

Quick reference covering the three data sources in this architecture: their role, key concepts, Python APIs, and local development equivalents.

---

## Google Cloud Storage (GCS)

### Role in this architecture
Document store — substitutes for Box. Holds raw and chunked documents ingested from the enterprise document repository. The ingestion pipeline writes here; the embedding step reads from here.

### Key concepts

| Concept | Description |
|---|---|
| **Bucket** | Top-level container, globally unique name. Analogous to a filesystem root or S3 bucket. |
| **Object (Blob)** | A file stored in a bucket. Identified by a key (e.g. `raw/report.md`). No real folders — prefixes like `raw/` are just naming conventions. |
| **Prefix** | A string filter used to simulate folder structure when listing objects. |
| **Content type** | MIME type stored with each object (e.g. `text/markdown`). |

### Python API (`google-cloud-storage`)

```python
from google.cloud import storage

client = storage.Client(project="gcp-rag-poc")

# List objects under a prefix
blobs = client.list_blobs("rag-poc-documents-dev", prefix="raw/")

# Download a file
blob = client.bucket("rag-poc-documents-dev").blob("raw/report.md")
content = blob.download_as_text()

# Upload a file
blob.upload_from_filename("report.md", content_type="text/markdown")
```

### Local equivalent
**`fake-gcs-server`** — a Docker container that implements the GCS HTTP API locally.

| Config | Value |
|---|---|
| Image | `fsouza/fake-gcs-server:latest` |
| Port | `4443` |
| Env var | `GCS_EMULATOR_HOST=http://localhost:4443` |

To point the client at the local emulator, pass `AnonymousCredentials` and a custom `api_endpoint`:

```python
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage

client = storage.Client(
    project="gcp-rag-poc",
    credentials=AnonymousCredentials(),
    client_options=ClientOptions(api_endpoint="http://localhost:4443"),
)
```

---

## BigQuery

### Role in this architecture
Global structured data store — holds enterprise-wide KPIs and product line performance metrics. Queried at runtime by the Structured Retriever via NL-to-SQL.

### Key concepts

| Concept | Description |
|---|---|
| **Dataset** | A namespace for tables, analogous to a database schema. |
| **Table** | Columnar, append-optimised storage. Strongly typed schema. |
| **Job** | All queries and loads run as asynchronous jobs. The client handles polling by default. |
| **`insert_rows_json`** | Streaming inserts — rows available immediately but bypass the load job pipeline. Good for small batches and emulator use. |
| **`query(sql).result()`** | Executes a SQL query and blocks until the result is ready. |

### Python API (`google-cloud-bigquery`)

```python
from google.cloud import bigquery

client = bigquery.Client(project="gcp-rag-poc")

# Query
rows = client.query("""
    SELECT product_line, SUM(revenue_usd) AS total_revenue
    FROM `gcp-rag-poc.global_metrics.global_metrics`
    WHERE region = 'EMEA'
    GROUP BY product_line
    ORDER BY total_revenue DESC
    LIMIT 5
""").result()

for row in rows:
    print(row["product_line"], row["total_revenue"])
```

### Local equivalent
**`bigquery-emulator`** — implements the BigQuery REST and gRPC APIs locally.

| Config | Value |
|---|---|
| Image | `ghcr.io/goccy/bigquery-emulator:latest` (runs under Rosetta on Apple Silicon) |
| REST port | `9050` |
| gRPC port | `9060` |
| Env var | `BIGQUERY_EMULATOR_HOST=http://localhost:9050` |

```python
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery

client = bigquery.Client(
    project="gcp-rag-poc",
    credentials=AnonymousCredentials(),
    client_options=ClientOptions(api_endpoint="http://localhost:9050"),
)
```

> **Emulator limitations:** not all BigQuery features are supported (e.g. some ML functions, advanced window functions). Standard SQL queries and DML work reliably.

---

## Cloud SQL / PostgreSQL (Snowflake substitute)

### Role in this architecture
Regional structured data store — holds regional P&L, product-level metrics, and country-level breakdowns. Substitutes for Snowflake in the POC. Queried at runtime by the Structured Retriever via NL-to-SQL.

### Key concepts

| Concept | Description |
|---|---|
| **Instance** | A managed PostgreSQL server on GCP (Cloud SQL). In production: `rag-poc-regional-dev`. |
| **Schema** | A namespace within a database (e.g. `regional`). Analogous to a BigQuery dataset. |
| **Table** | Standard relational table with typed columns. |
| **Connection** | Cloud SQL connections in production go via the **Cloud SQL Auth Proxy** — a sidecar that handles IAM-based authentication. Locally, connect directly via `host:port`. |

### Python API (`psycopg`)

```python
import psycopg

conn = psycopg.connect(
    host="localhost", port=5432,
    user="rag", password="rag", dbname="regional"
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT country, product_line, profit_margin_pct
        FROM regional.regional_metrics
        WHERE region = %s AND risk_score > %s
        ORDER BY profit_margin_pct ASC
        LIMIT 10
    """, ("EMEA", 7.0))
    rows = cur.fetchall()
```

> Always use parameterised queries (`%s`) — never string-format user input into SQL.

### Local equivalent
**`postgres:16`** Docker container — a standard PostgreSQL instance, no emulation layer needed.

| Config | Value |
|---|---|
| Image | `postgres:16` |
| Port | `5432` |
| Database | `regional` |
| Schema | `regional` |
| Table | `regional_metrics` |

No credential tricks needed — connect directly with host/port/user/password.

---

## Summary

| | GCS | BigQuery | Cloud SQL (Snowflake) |
|---|---|---|---|
| **Data type** | Unstructured (documents) | Structured (analytics) | Structured (operational) |
| **Query interface** | Object key / prefix | SQL | SQL |
| **Python library** | `google-cloud-storage` | `google-cloud-bigquery` | `psycopg` |
| **Local substitute** | `fake-gcs-server` | `bigquery-emulator` | `postgres:16` |
| **Auth (local)** | `AnonymousCredentials` + `api_endpoint` | `AnonymousCredentials` + `api_endpoint` | Direct host/port |
| **Auth (GCP)** | Service account via ADC | Service account via ADC | Cloud SQL Auth Proxy + IAM |
| **Used in RAG for** | Document ingestion & storage | Global metrics retrieval | Regional metrics retrieval |
