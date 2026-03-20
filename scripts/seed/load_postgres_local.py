"""
Load regional_metrics seed data into the local PostgreSQL container.

Creates schema and table if they do not exist. Clears existing rows before loading
so the script is safe to re-run.

Auto-generates seed data if data/seed/regional_metrics.csv is missing.
"""

import csv
import os
from pathlib import Path

import psycopg

SEED_FILE = Path(__file__).parents[2] / "data" / "seed" / "regional_metrics.csv"

CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS regional"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS regional.regional_metrics (
    id              INTEGER,
    date            DATE,
    year            INTEGER,
    quarter         VARCHAR(2),
    region          VARCHAR(10),
    country         VARCHAR(100),
    product_line    VARCHAR(100),
    revenue_usd     NUMERIC(18, 2),
    cost_usd        NUMERIC(18, 2),
    profit_usd      NUMERIC(18, 2),
    profit_margin_pct NUMERIC(6, 2),
    market_share_pct  NUMERIC(6, 2),
    risk_score      NUMERIC(4, 1)
)
"""

TRUNCATE_TABLE = "TRUNCATE TABLE regional.regional_metrics"


def _ensure_seed_file() -> None:
    if not SEED_FILE.exists():
        print("Seed file not found — generating structured data...")
        from scripts.seed.generate_structured import generate_regional_metrics, write_csv
        write_csv(generate_regional_metrics(), SEED_FILE)


def _connection() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        user=os.environ.get("POSTGRES_USER", "rag"),
        password=os.environ.get("POSTGRES_PASSWORD", "rag"),
        dbname=os.environ.get("POSTGRES_DB", "regional"),
    )


def load() -> int:
    _ensure_seed_file()

    with _connection() as conn, conn.cursor() as cur:
        cur.execute(CREATE_SCHEMA)
        cur.execute(CREATE_TABLE)
        cur.execute(TRUNCATE_TABLE)

        with open(SEED_FILE, newline="") as f:
            reader = csv.DictReader(f)
            rows = [
                (
                    int(r["id"]), r["date"], int(r["year"]), r["quarter"],
                    r["region"], r["country"], r["product_line"],
                    float(r["revenue_usd"]), float(r["cost_usd"]), float(r["profit_usd"]),
                    float(r["profit_margin_pct"]), float(r["market_share_pct"]),
                    float(r["risk_score"]),
                )
                for r in reader
            ]

        cur.executemany(
            """
            INSERT INTO regional.regional_metrics VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            rows,
        )
        conn.commit()

    print(f"Loaded {len(rows)} rows into regional.regional_metrics")
    return len(rows)


if __name__ == "__main__":
    load()
