"""
Load global_metrics seed data into the local BigQuery emulator.

Creates dataset and table if they do not exist. Replaces existing rows on each run.

Auto-generates seed data if data/seed/global_metrics.csv is missing.
"""

import csv
import os
from pathlib import Path

from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery

SEED_FILE = Path(__file__).parents[2] / "data" / "seed" / "global_metrics.csv"

DATASET_ID = "global_metrics"
TABLE_ID = "global_metrics"

SCHEMA = [
    bigquery.SchemaField("id", "INTEGER"),
    bigquery.SchemaField("date", "DATE"),
    bigquery.SchemaField("year", "INTEGER"),
    bigquery.SchemaField("quarter", "STRING"),
    bigquery.SchemaField("product_line", "STRING"),
    bigquery.SchemaField("region", "STRING"),
    bigquery.SchemaField("revenue_usd", "FLOAT"),
    bigquery.SchemaField("cost_usd", "FLOAT"),
    bigquery.SchemaField("profit_usd", "FLOAT"),
    bigquery.SchemaField("profit_margin_pct", "FLOAT"),
    bigquery.SchemaField("yoy_growth_pct", "FLOAT"),
    bigquery.SchemaField("headcount", "INTEGER"),
    bigquery.SchemaField("customer_count", "INTEGER"),
]


def _ensure_seed_file() -> None:
    if not SEED_FILE.exists():
        print("Seed file not found — generating structured data...")
        from scripts.seed.generate_structured import generate_global_metrics, write_csv
        write_csv(generate_global_metrics(), SEED_FILE)


def _client() -> bigquery.Client:
    return bigquery.Client(
        project=os.environ.get("GCP_PROJECT_ID", "gcp-rag-poc"),
        credentials=AnonymousCredentials(),
        client_options=ClientOptions(
            api_endpoint=os.environ.get("BIGQUERY_EMULATOR_HOST", "http://localhost:9050")
        ),
    )


def load() -> int:
    _ensure_seed_file()

    client = _client()
    project = os.environ.get("GCP_PROJECT_ID", "gcp-rag-poc")

    # Create dataset
    dataset_ref = bigquery.Dataset(f"{project}.{DATASET_ID}")
    dataset_ref.location = "US"
    client.create_dataset(dataset_ref, exists_ok=True)

    # Create or replace table
    table_ref = f"{project}.{DATASET_ID}.{TABLE_ID}"
    table = bigquery.Table(table_ref, schema=SCHEMA)
    client.create_table(table, exists_ok=True)

    # Load rows
    with open(SEED_FILE, newline="") as f:
        reader = csv.DictReader(f)
        rows = [
            {
                "id": int(r["id"]),
                "date": r["date"],
                "year": int(r["year"]),
                "quarter": r["quarter"],
                "product_line": r["product_line"],
                "region": r["region"],
                "revenue_usd": float(r["revenue_usd"]),
                "cost_usd": float(r["cost_usd"]),
                "profit_usd": float(r["profit_usd"]),
                "profit_margin_pct": float(r["profit_margin_pct"]),
                "yoy_growth_pct": float(r["yoy_growth_pct"]),
                "headcount": int(r["headcount"]),
                "customer_count": int(r["customer_count"]),
            }
            for r in reader
        ]

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")

    print(f"Loaded {len(rows)} rows into {table_ref}")
    return len(rows)


if __name__ == "__main__":
    load()
