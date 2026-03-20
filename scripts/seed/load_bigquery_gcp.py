"""
Load global_metrics seed data into BigQuery (GCP).

Uses Application Default Credentials. Auto-generates seed data if missing.
"""

import csv
import os
from pathlib import Path

from google.cloud import bigquery

SEED_FILE = Path(__file__).parents[2] / "data" / "seed" / "global_metrics.csv"

DATASET_ID = "global_metrics"
TABLE_ID = "global_metrics"


def _ensure_seed_file() -> None:
    if not SEED_FILE.exists():
        print("Seed file not found — generating structured data...")
        from scripts.seed.generate_structured import generate_global_metrics, write_csv
        write_csv(generate_global_metrics(), SEED_FILE)


def load() -> int:
    _ensure_seed_file()

    project = os.environ["GCP_PROJECT_ID"]
    client = bigquery.Client(project=project)
    table_ref = f"{project}.{DATASET_ID}.{TABLE_ID}"

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
