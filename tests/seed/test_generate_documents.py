"""Tests for document seed data generation."""

import pytest
from scripts.seed.generate_documents import (
    strategy_memo,
    risk_assessment,
    remediation_guidance,
    regulatory_note,
)


def test_strategy_memo_filename_contains_product_line_and_region():
    filename, _ = strategy_memo("Retail Banking", "EMEA", "Q3", 2024)
    assert "retail_banking" in filename
    assert "emea" in filename


def test_strategy_memo_content_contains_product_line():
    _, content = strategy_memo("Wealth Management", "APAC", "Q1", 2024)
    assert "Wealth Management" in content


def test_strategy_memo_content_contains_year_and_quarter():
    _, content = strategy_memo("Insurance", "AMER", "Q2", 2023)
    assert "2023" in content
    assert "Q2" in content


def test_risk_assessment_filename_contains_project_name():
    filename, _ = risk_assessment("Project Apollo", "EMEA", 2024)
    assert "project_apollo" in filename


def test_risk_assessment_content_contains_project_name():
    _, content = risk_assessment("Project Apollo", "EMEA", 2024)
    assert "Project Apollo" in content


def test_risk_assessment_content_contains_financial_exposure():
    _, content = risk_assessment("Project Horizon", "APAC", 2024)
    assert "exposure" in content.lower()


def test_remediation_guidance_filename_contains_product_line():
    filename, _ = remediation_guidance("Corporate Banking")
    assert "corporate_banking" in filename


def test_remediation_guidance_content_contains_underperformance_criteria():
    _, content = remediation_guidance("Retail Banking")
    assert "Underperformance Criteria" in content


def test_remediation_guidance_content_contains_escalation_path():
    _, content = remediation_guidance("Retail Banking")
    assert "Escalation Path" in content


def test_regulatory_note_filename_contains_topic_and_year():
    filename, _ = regulatory_note("Consumer Duty", 2024)
    assert "consumer_duty" in filename
    assert "2024" in filename


def test_regulatory_note_content_contains_topic():
    _, content = regulatory_note("Basel IV Capital Requirements", 2024)
    assert "Basel IV Capital Requirements" in content
