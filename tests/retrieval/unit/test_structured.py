"""Unit tests for the SQL safety guard in the structured retriever."""

import pytest

from src.retrieval.structured import _is_safe_sql


@pytest.mark.parametrize("sql", [
    "SELECT * FROM regional.regional_metrics",
    "SELECT product_line, revenue_usd FROM global_metrics.global_metrics LIMIT 10",
    "select id, date from t where year = 2024",
    "SELECT\n  product_line,\n  region\nFROM t",
])
def test_valid_select_statements_are_safe(sql):
    assert _is_safe_sql(sql)


@pytest.mark.parametrize("sql,label", [
    ("INSERT INTO t VALUES (1)", "INSERT"),
    ("UPDATE t SET x = 1 WHERE id = 1", "UPDATE"),
    ("DELETE FROM t WHERE id = 1", "DELETE"),
    ("DROP TABLE t", "DROP"),
    ("CREATE TABLE foo (id INTEGER)", "CREATE"),
    ("ALTER TABLE foo ADD COLUMN bar TEXT", "ALTER"),
    ("TRUNCATE TABLE t", "TRUNCATE"),
    ("insert into t values (1)", "lowercase INSERT"),
    ("Select id from t; DROP TABLE t", "SELECT with trailing DROP"),
])
def test_dangerous_statements_are_rejected(sql, label):
    assert not _is_safe_sql(sql), f"Expected rejection for: {label}"


@pytest.mark.parametrize("sql", [
    "WITH cte AS (SELECT 1) DELETE FROM t",
    "",
    "EXPLAIN SELECT * FROM t",
    "-- SELECT * FROM t",
])
def test_non_select_start_is_rejected(sql):
    assert not _is_safe_sql(sql)
