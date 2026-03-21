"""Unit tests for context fusion."""

import pytest

from src.retrieval.fusion import fuse, ContextItem
from src.retrieval.semantic import SemanticResult
from src.retrieval.structured import StructuredResult


def _semantic(chunk_id: str, score: float, text: str = "chunk text") -> SemanticResult:
    return SemanticResult(
        chunk_id=chunk_id,
        text=text,
        section="Section",
        doc_id="doc1",
        source_key=f"raw/{chunk_id}.md",
        score=score,
    )


def _structured(source: str = "bigquery", rows: list | None = None, error: str | None = None) -> StructuredResult:
    return StructuredResult(
        source=source,
        columns=["product_line", "revenue_usd"],
        rows=rows if rows is not None else [("Retail", 1000000.0)],
        generated_sql="SELECT product_line, revenue_usd FROM t LIMIT 5",
        error=error,
    )


def test_semantic_results_are_sorted_by_score_descending():
    results = fuse(
        [_semantic("a", 0.5), _semantic("b", 0.9), _semantic("c", 0.3)],
        [],
    )
    scores = [i.score for i in results.items if i.type == "semantic"]
    assert scores == sorted(scores, reverse=True)


def test_duplicate_chunk_ids_keep_highest_scored_copy():
    results = fuse(
        [_semantic("a", 0.9), _semantic("a", 0.4)],
        [],
    )
    semantic_items = [i for i in results.items if i.type == "semantic"]
    assert len(semantic_items) == 1
    assert semantic_items[0].score == pytest.approx(0.9)


def test_structured_results_appear_in_fused_output():
    results = fuse([], [_structured("bigquery"), _structured("cloudsql")])
    structured_items = [i for i in results.items if i.type == "structured"]
    assert len(structured_items) == 2


def test_structured_results_with_errors_are_excluded():
    results = fuse([], [_structured(error="SQL failed"), _structured()])
    structured_items = [i for i in results.items if i.type == "structured"]
    assert len(structured_items) == 1


def test_structured_items_have_score_of_1():
    results = fuse([], [_structured()])
    structured_items = [i for i in results.items if i.type == "structured"]
    assert structured_items[0].score == pytest.approx(1.0)


def test_output_is_truncated_to_max_context_items():
    semantic = [_semantic(str(i), float(i) / 10) for i in range(10)]
    results = fuse(semantic, [], max_context_items=3)
    assert len(results.items) == 3


def test_mixed_results_sorted_with_high_scoring_semantic_above_structured():
    results = fuse(
        [_semantic("a", 1.5)],  # score > 1.0 (structured)
        [_structured()],
        max_context_items=10,
    )
    assert results.items[0].type == "semantic"
    assert results.items[1].type == "structured"


def test_structured_content_includes_column_headers_and_rows():
    results = fuse([], [_structured(rows=[("Retail", 1_000_000.0), ("Wealth", 800_000.0)])])
    content = results.items[0].content
    assert "product_line" in content
    assert "Retail" in content
    assert "Wealth" in content


def test_empty_inputs_return_empty_fused_context():
    results = fuse([], [])
    assert results.items == []
