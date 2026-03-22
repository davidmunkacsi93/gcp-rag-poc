"""Unit tests for the query router."""

import pytest

from src.retrieval.router import route


def test_metric_keywords_activate_structured_paths():
    decision = route("What was the revenue growth in EMEA last quarter?")
    assert decision.structured_bigquery
    assert decision.structured_cloudsql


def test_document_keywords_activate_semantic_path():
    decision = route("Is there any remediation guidance for the Retail product line?")
    assert decision.semantic
    assert not decision.structured_bigquery
    assert not decision.structured_cloudsql


def test_ambiguous_query_activates_both_paths():
    decision = route("Tell me something interesting")
    assert decision.semantic
    assert decision.structured_bigquery
    assert decision.structured_cloudsql


def test_federated_query_activates_all_paths():
    decision = route("What is the revenue exposure and is there risk guidance for Project Apollo?")
    assert decision.semantic
    assert decision.structured_bigquery
    assert decision.structured_cloudsql


def test_risk_keyword_sets_risk_assessment_filter():
    decision = route("What are the key risks identified in the latest report?")
    assert decision.doc_type_filter == "risk_assessment"


def test_remediation_keyword_sets_remediation_filter():
    decision = route("Show me the remediation guidance for corporate banking")
    assert decision.doc_type_filter == "remediation"


def test_regulatory_keyword_sets_regulatory_filter():
    decision = route("What are the regulatory requirements under Basel IV?")
    assert decision.doc_type_filter == "regulatory"


def test_compliance_keyword_sets_regulatory_filter():
    decision = route("What compliance obligations apply to our operations?")
    assert decision.doc_type_filter == "regulatory"


def test_strategy_keyword_sets_strategy_memo_filter():
    decision = route("What is the strategy for Investment Banking in EMEA?")
    assert decision.doc_type_filter == "strategy_memo"


def test_due_diligence_sets_risk_assessment_filter():
    decision = route("Run a preliminary due diligence summary for Project Apollo")
    assert decision.doc_type_filter == "risk_assessment"


def test_metric_only_query_has_no_doc_type_filter():
    decision = route("What was headcount growth by region in Q3?")
    assert decision.doc_type_filter is None
    assert not decision.semantic
