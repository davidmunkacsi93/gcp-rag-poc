"""Tests for structured seed data generation."""

import pytest
from scripts.seed.generate_structured import generate_global_metrics, generate_regional_metrics, REGIONS, PRODUCT_LINES


def test_global_metrics_returns_requested_row_count():
    rows = generate_global_metrics(n=10)
    assert len(rows) == 10


def test_global_metrics_contains_required_fields():
    required = {"id", "date", "year", "quarter", "product_line", "region",
                "revenue_usd", "cost_usd", "profit_usd", "profit_margin_pct",
                "yoy_growth_pct", "headcount", "customer_count"}
    rows = generate_global_metrics(n=1)
    assert required == set(rows[0].keys())


def test_global_metrics_profit_is_revenue_minus_cost():
    rows = generate_global_metrics(n=50)
    for row in rows:
        assert round(row["profit_usd"], 2) == round(row["revenue_usd"] - row["cost_usd"], 2)


def test_global_metrics_region_values_are_valid():
    rows = generate_global_metrics(n=100)
    for row in rows:
        assert row["region"] in REGIONS


def test_global_metrics_product_line_values_are_valid():
    rows = generate_global_metrics(n=100)
    for row in rows:
        assert row["product_line"] in PRODUCT_LINES


def test_regional_metrics_returns_requested_row_count():
    rows = generate_regional_metrics(n=10)
    assert len(rows) == 10


def test_regional_metrics_contains_required_fields():
    required = {"id", "date", "year", "quarter", "region", "country", "product_line",
                "revenue_usd", "cost_usd", "profit_usd", "profit_margin_pct",
                "market_share_pct", "risk_score"}
    rows = generate_regional_metrics(n=1)
    assert required == set(rows[0].keys())


def test_regional_metrics_country_belongs_to_region():
    from scripts.seed.generate_structured import COUNTRIES
    rows = generate_regional_metrics(n=100)
    for row in rows:
        assert row["country"] in COUNTRIES[row["region"]]


def test_regional_metrics_risk_score_within_bounds():
    rows = generate_regional_metrics(n=100)
    for row in rows:
        assert 1.0 <= row["risk_score"] <= 10.0
