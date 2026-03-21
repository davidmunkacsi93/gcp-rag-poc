"""Tests for the parser module."""

import pytest

from src.ingestion.parser import parse_document


def test_parse_document_extracts_title_from_first_h1():
    raw = "# My Document Title\n\nSome content here."
    doc = parse_document(raw, "raw/strategy_memo_q1.md")
    assert doc.title == "My Document Title"


def test_parse_document_falls_back_to_filename_stem_when_no_h1():
    raw = "Some content without a heading."
    doc = parse_document(raw, "raw/strategy_memo_q1.md")
    assert doc.title == "strategy_memo_q1"


def test_parse_document_infers_doc_type_strategy_memo():
    doc = parse_document("content", "raw/strategy_memo_2024.md")
    assert doc.doc_type == "strategy_memo"


def test_parse_document_infers_doc_type_risk_assessment():
    doc = parse_document("content", "raw/risk_assessment_q3.md")
    assert doc.doc_type == "risk_assessment"


def test_parse_document_infers_doc_type_remediation():
    doc = parse_document("content", "raw/remediation_plan.md")
    assert doc.doc_type == "remediation"


def test_parse_document_infers_doc_type_regulatory():
    doc = parse_document("content", "raw/regulatory_update.md")
    assert doc.doc_type == "regulatory"


def test_parse_document_infers_doc_type_unknown_for_unrecognised_filename():
    doc = parse_document("content", "raw/quarterly_report.md")
    assert doc.doc_type == "unknown"


def test_parse_document_splits_sections_on_h2_headings():
    raw = "# Title\n\n## Section One\n\nBody one.\n\n## Section Two\n\nBody two."
    doc = parse_document(raw, "raw/strategy_memo_test.md")
    headings = [s["heading"] for s in doc.sections]
    assert "Section One" in headings
    assert "Section Two" in headings


def test_parse_document_splits_sections_on_h3_headings():
    raw = "# Title\n\n### Sub Section\n\nBody text here."
    doc = parse_document(raw, "raw/strategy_memo_test.md")
    headings = [s["heading"] for s in doc.sections]
    assert "Sub Section" in headings


def test_parse_document_captures_text_before_first_heading_as_section_under_title():
    raw = "# Doc Title\n\nIntroductory paragraph.\n\n## Section A\n\nSection A body."
    doc = parse_document(raw, "raw/strategy_memo_test.md")
    first_section = doc.sections[0]
    assert first_section["heading"] == "Doc Title"
    assert "Introductory paragraph." in first_section["body"]


def test_parse_document_returns_single_empty_body_section_for_document_with_no_body():
    raw = ""
    doc = parse_document(raw, "raw/strategy_memo_empty.md")
    assert len(doc.sections) == 1
    assert doc.sections[0]["body"] == ""
