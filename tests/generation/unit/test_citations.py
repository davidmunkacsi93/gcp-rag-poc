"""Unit tests for the citation assembler."""

import pytest

from src.generation.citations import Citation, extract_citations
from src.retrieval.fusion import ContextItem, FusedContext


def _context(*items: ContextItem) -> FusedContext:
    return FusedContext(items=list(items))


def _semantic(source_ref: str) -> ContextItem:
    return ContextItem(type="semantic", content="text", source_ref=source_ref, score=0.9)


def _structured(sql: str) -> ContextItem:
    return ContextItem(type="structured", content="rows", source_ref=sql, score=1.0)


def test_single_semantic_citation_is_extracted():
    answer = "The result. [Source: gs://bucket/doc.pdf, Section 3]"
    context = _context(_semantic("gs://bucket/doc.pdf"))
    citations = extract_citations(answer, context)
    assert len(citations) == 1
    assert citations[0].source_key == "gs://bucket/doc.pdf"
    assert citations[0].section == "Section 3"
    assert citations[0].type == "semantic"
    assert citations[0].generated_sql == ""


def test_single_structured_citation_is_extracted_with_generated_sql():
    sql = "SELECT revenue FROM t LIMIT 5"
    answer = "Revenue data. [Source: SQL, bigquery]"
    context = _context(_structured(sql))
    citations = extract_citations(answer, context)
    assert len(citations) == 1
    assert citations[0].source_key == "SQL"
    assert citations[0].section == "N/A"
    assert citations[0].type == "structured"
    assert citations[0].generated_sql == sql


def test_multiple_citations_extracted_in_order():
    answer = (
        "Point one. [Source: gs://b/a.pdf, Intro] "
        "Point two. [Source: gs://b/b.pdf, Summary]"
    )
    context = _context(_semantic("gs://b/a.pdf"), _semantic("gs://b/b.pdf"))
    citations = extract_citations(answer, context)
    assert len(citations) == 2
    assert citations[0].source_key == "gs://b/a.pdf"
    assert citations[1].source_key == "gs://b/b.pdf"


def test_duplicate_citations_are_deduplicated():
    answer = (
        "[Source: gs://b/doc.pdf, Section 1] "
        "[Source: gs://b/doc.pdf, Section 1]"
    )
    context = _context(_semantic("gs://b/doc.pdf"))
    citations = extract_citations(answer, context)
    assert len(citations) == 1


def test_same_source_different_section_are_not_deduplicated():
    answer = "[Source: gs://b/doc.pdf, Section 1] [Source: gs://b/doc.pdf, Section 2]"
    context = _context(_semantic("gs://b/doc.pdf"))
    citations = extract_citations(answer, context)
    assert len(citations) == 2


def test_answer_with_no_citations_returns_empty_list():
    answer = "There is no information available."
    citations = extract_citations(answer, _context(_semantic("gs://b/doc.pdf")))
    assert citations == []


def test_malformed_citation_missing_bracket_is_ignored():
    answer = "See Source: gs://b/doc.pdf, Section 1 for details."
    citations = extract_citations(answer, _context(_semantic("gs://b/doc.pdf")))
    assert citations == []


def test_malformed_citation_missing_comma_is_ignored():
    answer = "[Source: gs://b/doc.pdf Section 1]"
    citations = extract_citations(answer, _context(_semantic("gs://b/doc.pdf")))
    assert citations == []


def test_mixed_semantic_and_structured_citations():
    sql = "SELECT * FROM metrics"
    answer = "[Source: gs://b/doc.pdf, Appendix] [Source: SQL, bigquery]"
    context = _context(_semantic("gs://b/doc.pdf"), _structured(sql))
    citations = extract_citations(answer, context)
    assert len(citations) == 2
    types = {c.type for c in citations}
    assert types == {"semantic", "structured"}
