"""Unit tests for the prompt builder."""

import pytest

from src.generation.config import GenerationConfig
from src.generation.prompt import build_prompt, _SYSTEM_INSTRUCTION
from src.retrieval.fusion import ContextItem, FusedContext


def _semantic(source_ref: str, content: str, score: float = 0.9) -> ContextItem:
    return ContextItem(type="semantic", content=content, source_ref=source_ref, score=score)


def _structured(sql: str, content: str) -> ContextItem:
    return ContextItem(type="structured", content=content, source_ref=sql, score=1.0)


def _context(*items: ContextItem) -> FusedContext:
    return FusedContext(items=list(items))


def test_system_instruction_contains_answer_only_from_context_directive():
    prompt = build_prompt("query", _context(_semantic("gs://b/doc.pdf", "text")))
    assert "ONLY" in prompt
    assert "context" in prompt.lower()


def test_system_instruction_contains_insufficient_information_fallback():
    prompt = build_prompt("query", _context(_semantic("gs://b/doc.pdf", "text")))
    assert "I don't have enough information to answer this question." in prompt


def test_semantic_items_formatted_as_numbered_reference_blocks():
    context = _context(
        _semantic("gs://bucket/a.pdf", "chunk A"),
        _semantic("gs://bucket/b.pdf", "chunk B"),
    )
    prompt = build_prompt("query", context)
    assert "[1]" in prompt
    assert "[2]" in prompt
    assert "chunk A" in prompt
    assert "chunk B" in prompt


def test_semantic_item_includes_source_ref_and_score():
    context = _context(_semantic("gs://bucket/doc.pdf", "some text", score=0.85))
    prompt = build_prompt("query", context)
    assert "gs://bucket/doc.pdf" in prompt
    assert "0.850" in prompt


def test_structured_item_includes_structured_data_label():
    context = _context(_structured("SELECT * FROM t", "col_a | col_b\n1 | 2"))
    prompt = build_prompt("query", context)
    assert "Structured Data" in prompt


def test_structured_item_includes_sql_and_content():
    context = _context(_structured("SELECT revenue FROM t LIMIT 5", "revenue\n1000"))
    prompt = build_prompt("query", context)
    assert "SELECT revenue FROM t LIMIT 5" in prompt
    assert "1000" in prompt


def test_user_query_appears_at_end_of_prompt():
    query = "What were the top underperforming product lines?"
    prompt = build_prompt(query, _context(_semantic("src", "text")))
    assert prompt.endswith(query)


def test_context_truncation_respects_max_context_tokens_budget():
    # Create items whose combined token estimate clearly exceeds a small budget
    large_content = "x" * 400  # ~100 tokens per item
    items = [_semantic(f"src/{i}", large_content, score=float(i)) for i in range(10)]
    config = GenerationConfig(max_context_tokens=200)
    prompt = build_prompt("query", FusedContext(items=items), config)
    # Tail items (lowest index = lowest score) should be dropped
    assert "src/0" not in prompt


def test_truncation_keeps_higher_scored_items_over_lower_scored():
    large_content = "y" * 400
    items = [_semantic(f"src/{i}", large_content, score=float(i)) for i in range(5)]
    config = GenerationConfig(max_context_tokens=300)
    prompt = build_prompt("query", FusedContext(items=items), config)
    # Highest-scored item (src/4) should be present
    assert "src/4" in prompt


def test_empty_context_returns_prompt_with_system_instruction_and_query():
    query = "any question"
    prompt = build_prompt(query, FusedContext(items=[]))
    assert _SYSTEM_INSTRUCTION in prompt
    assert query in prompt
