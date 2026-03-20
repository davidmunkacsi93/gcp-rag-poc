"""
Generate synthetic financial services structured seed data.

Outputs:
  data/seed/global_metrics.csv   — ~1000 rows of global product line performance
  data/seed/regional_metrics.csv — ~1000 rows of regional P&L breakdown
"""

import csv
import random
from datetime import date
from pathlib import Path

from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

OUTPUT_DIR = Path(__file__).parents[2] / "data" / "seed"

PRODUCT_LINES = [
    "Retail Banking",
    "Wealth Management",
    "Corporate Banking",
    "Investment Banking",
    "Insurance",
    "Asset Management",
    "Trade Finance",
    "Treasury Services",
]

REGIONS = ["EMEA", "APAC", "AMER"]

COUNTRIES = {
    "EMEA": ["United Kingdom", "Germany", "France", "UAE", "South Africa", "Netherlands"],
    "APAC": ["Japan", "Australia", "Singapore", "Hong Kong", "India", "South Korea"],
    "AMER": ["United States", "Canada", "Brazil", "Mexico", "Argentina", "Colombia"],
}

QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
YEARS = [2022, 2023, 2024]


def _quarter_start(year: int, quarter: str) -> date:
    month = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}[quarter]
    return date(year, month, 1)


def generate_global_metrics(n: int = 1000) -> list[dict]:
    rows = []
    for i in range(n):
        year = random.choice(YEARS)
        quarter = random.choice(QUARTERS)
        product_line = random.choice(PRODUCT_LINES)
        region = random.choice(REGIONS)

        revenue = round(random.uniform(50_000_000, 500_000_000), 2)
        cost_ratio = random.uniform(0.45, 0.80)
        cost = round(revenue * cost_ratio, 2)
        profit = round(revenue - cost, 2)
        profit_margin = round((profit / revenue) * 100, 2)
        yoy_growth = round(random.uniform(-15.0, 25.0), 2)
        headcount = random.randint(200, 5000)
        customer_count = random.randint(10_000, 2_000_000)

        rows.append({
            "id": i + 1,
            "date": _quarter_start(year, quarter).isoformat(),
            "year": year,
            "quarter": quarter,
            "product_line": product_line,
            "region": region,
            "revenue_usd": revenue,
            "cost_usd": cost,
            "profit_usd": profit,
            "profit_margin_pct": profit_margin,
            "yoy_growth_pct": yoy_growth,
            "headcount": headcount,
            "customer_count": customer_count,
        })
    return rows


def generate_regional_metrics(n: int = 1000) -> list[dict]:
    rows = []
    for i in range(n):
        year = random.choice(YEARS)
        quarter = random.choice(QUARTERS)
        region = random.choice(REGIONS)
        country = random.choice(COUNTRIES[region])
        product_line = random.choice(PRODUCT_LINES)

        revenue = round(random.uniform(5_000_000, 150_000_000), 2)
        cost_ratio = random.uniform(0.50, 0.85)
        cost = round(revenue * cost_ratio, 2)
        profit = round(revenue - cost, 2)
        profit_margin = round((profit / revenue) * 100, 2)
        market_share = round(random.uniform(1.0, 25.0), 2)
        risk_score = round(random.uniform(1.0, 10.0), 1)

        rows.append({
            "id": i + 1,
            "date": _quarter_start(year, quarter).isoformat(),
            "year": year,
            "quarter": quarter,
            "region": region,
            "country": country,
            "product_line": product_line,
            "revenue_usd": revenue,
            "cost_usd": cost,
            "profit_usd": profit,
            "profit_margin_pct": profit_margin,
            "market_share_pct": market_share,
            "risk_score": risk_score,
        })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows → {path}")


if __name__ == "__main__":
    write_csv(generate_global_metrics(), OUTPUT_DIR / "global_metrics.csv")
    write_csv(generate_regional_metrics(), OUTPUT_DIR / "regional_metrics.csv")
