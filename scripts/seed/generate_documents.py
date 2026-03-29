"""
Generate synthetic financial services documents as Markdown files.

Outputs 15 documents to data/seed/documents/:
  - Strategy memos (4)
  - Risk assessment reports (4, including Project Apollo)
  - Remediation guidance by product line (4)
  - Regulatory compliance notes (3)
"""

import random
from datetime import date
from pathlib import Path

from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

OUTPUT_DIR = Path(__file__).parents[2] / "data" / "seed" / "documents"

PRODUCT_LINES = [
    "Retail Banking",
    "Wealth Management",
    "Corporate Banking",
    "Investment Banking",
]

REGIONS = ["EMEA", "APAC", "AMER"]


def strategy_memo(product_line: str, region: str, quarter: str, year: int) -> tuple[str, str]:
    filename = f"strategy_memo_{product_line.lower().replace(' ', '_')}_{region.lower()}_{year}_{quarter.lower()}.md"
    initiatives = [fake.bs().capitalize() for _ in range(3)]
    risks = [fake.catch_phrase() for _ in range(2)]

    content = f"""# Strategic Memo — {product_line} {region} {quarter} {year}

**Classification:** Internal — Restricted
**Author:** {fake.name()}, Head of {product_line}
**Date:** {fake.date_between(start_date=date(year, 1, 1), end_date=date(year, 12, 31))}

## Executive Summary

This memo outlines the strategic priorities for {product_line} in {region} for {quarter} {year}.
Market conditions in {region} have shown {"improvement" if random.random() > 0.4 else "deterioration"} relative to
the prior quarter, with particular pressure on {"revenue growth" if random.random() > 0.5 else "cost efficiency"}.

## Strategic Priorities

{"".join(f"{i+1}. {initiative}\n" for i, initiative in enumerate(initiatives))}

## Key Risks

{"".join(f"- **{risk}**: Mitigation plan under review by the Risk Committee.\n" for risk in risks)}

## Resource Allocation

Headcount is expected to {"increase by {n}%" .format(n=random.randint(2, 15)) if random.random() > 0.5 else "remain flat"}
through end of {year}. Capital expenditure budget is set at ${random.randint(5, 50)}M for this period.

## Recommended Actions

- Accelerate digital channel adoption across {region} markets
- Review pricing strategy for {product_line} flagship products
- Strengthen risk governance framework in line with regulatory expectations

---
*This document is intended for internal distribution only.*
"""
    return filename, content


_RISK_ASSESSMENTS = {
    "Market Risk": [
        "Volatile interest rate environment may compress net interest margins across EMEA portfolios.",
        "FX exposure in APAC markets has increased following currency devaluation in key trading partners.",
        "Equity market downturn risk elevated due to geopolitical tensions affecting AMER operations.",
        "Spread widening in credit markets may reduce fair value of held-to-maturity bond portfolios.",
    ],
    "Credit Risk": [
        "Counterparty concentration in top-10 clients exceeds internal limits; requires immediate review.",
        "Non-performing loan ratio has risen above the 3% threshold in the retail segment.",
        "Collateral valuations have not been refreshed in over 12 months for a subset of corporate loans.",
        "Wholesale credit exposures to real estate sector represent 18% of total portfolio — above policy limit.",
    ],
    "Operational Risk": [
        "Legacy core banking system lacks automated reconciliation, increasing manual error risk.",
        "Third-party vendor for payment processing has no tested business continuity plan in place.",
        "Staff turnover in operations has reached 22%, creating key-person dependency on critical processes.",
        "Recent internal audit identified gaps in change management controls for technology deployments.",
    ],
    "Regulatory Risk": [
        "Programme activities fall within scope of DORA; ICT risk management framework must be updated by Q2.",
        "Pending MiFID II review may require re-papering of client agreements across 1,200 accounts.",
        "Basel IV capital floors will increase RWA by an estimated 8–12% if implemented without mitigation.",
        "Consumer Duty obligations require product fair value assessments to be completed before go-live.",
    ],
    "Reputational Risk": [
        "Media coverage of programme delays could affect client confidence in the bank's digital transformation.",
        "Data privacy incident in a related programme has heightened regulator scrutiny of this initiative.",
        "External benchmarking indicates peer firms have achieved similar objectives at 30% lower cost.",
        "ESG commitments linked to this programme have not been independently verified, creating disclosure risk.",
    ],
}


def risk_assessment(project_name: str, region: str, year: int) -> tuple[str, str]:
    filename = f"risk_assessment_{project_name.lower().replace(' ', '_')}_{year}.md"
    risk_items = [
        ("Market Risk", random.randint(1, 10), random.choice(_RISK_ASSESSMENTS["Market Risk"])),
        ("Credit Risk", random.randint(1, 10), random.choice(_RISK_ASSESSMENTS["Credit Risk"])),
        ("Operational Risk", random.randint(1, 10), random.choice(_RISK_ASSESSMENTS["Operational Risk"])),
        ("Regulatory Risk", random.randint(1, 10), random.choice(_RISK_ASSESSMENTS["Regulatory Risk"])),
        ("Reputational Risk", random.randint(1, 10), random.choice(_RISK_ASSESSMENTS["Reputational Risk"])),
    ]
    total_exposure = random.randint(10, 500)

    content = f"""# Risk Assessment Report — {project_name}

**Classification:** Confidential
**Prepared by:** {fake.name()}, Chief Risk Officer
**Review Date:** {fake.date_between(start_date=date(year, 1, 1), end_date=date(year, 12, 31))}
**Region:** {region}
**Status:** {"Under Review" if random.random() > 0.5 else "Approved"}

## Project Overview

{project_name} is a {"strategic initiative" if random.random() > 0.5 else "transformation programme"} targeting
{fake.bs()}. The programme has a total estimated financial exposure of **${total_exposure}M** across {region}.

## Risk Register

| Risk Category | Score (1-10) | Assessment |
|---|---|---|
{"".join(f"| {name} | {score} | {desc} |\n" for name, score, desc in risk_items)}

## Open Risk Items

{"".join(f"- **{name}** (Score: {score}): {desc} Escalation required if unresolved by next review cycle.\n" for name, score, desc in risk_items if score >= 7)}

## Financial Exposure Summary

- **Total Programme Exposure:** ${total_exposure}M
- **Contingency Reserve:** ${round(total_exposure * 0.15)}M
- **Approved Budget:** ${round(total_exposure * 0.85)}M

## Recommendations

1. Establish a dedicated risk working group for high-scoring items
2. Review escalation thresholds with the Board Risk Committee
3. Ensure regulatory obligations are mapped to programme milestones
4. Re-assess exposure quarterly until risk scores are below threshold

---
*This report is classified as Confidential. Distribution is restricted to named recipients.*
"""
    return filename, content


def remediation_guidance(product_line: str) -> tuple[str, str]:
    filename = f"remediation_guidance_{product_line.lower().replace(' ', '_')}.md"
    _remediation_steps = [
        "Conduct a root-cause analysis to identify the primary driver of underperformance.",
        "Submit a 30-day recovery plan to the Regional Performance Committee for approval.",
        "Implement weekly KPI tracking and share results with Group Finance.",
        "Engage frontline managers to identify operational blockers and escalate resource gaps.",
        "Review pricing and product mix to identify margin recovery opportunities.",
        "Freeze discretionary expenditure pending return to threshold performance.",
    ]
    steps = random.sample(_remediation_steps, 4)

    content = f"""# Remediation Guidance — {product_line}

**Classification:** Internal
**Owner:** {fake.name()}, Performance Management
**Last Updated:** {fake.date_this_year()}

## Context

This guidance applies to {product_line} business units that have reported underperformance against
quarterly targets. It is intended to support regional leads in structuring a response plan.

## Underperformance Criteria

A business unit is considered underperforming if any of the following thresholds are breached:

- Profit margin below **12%** for two consecutive quarters
- Revenue growth below **0%** year-on-year
- Risk score above **7.5** on the internal risk register
- Customer attrition rate exceeding **8%** in a rolling 12-month period

## Remediation Steps

{"".join(f"{i+1}. {step}\n" for i, step in enumerate(steps))}

## Escalation Path

| Severity | Owner | Timeline |
|---|---|---|
| Minor (1 metric breached) | Regional Head | 30 days |
| Moderate (2 metrics breached) | Business Line CEO | 14 days |
| Critical (3+ metrics breached) | Group CEO + Board | Immediate |

## Reporting Requirements

Affected business units must submit a remediation plan within **10 business days** of receiving
a formal underperformance notice. Progress reviews are held monthly until all metrics return
to threshold.

---
*For queries, contact the Group Performance Management Office.*
"""
    return filename, content


def regulatory_note(topic: str, year: int) -> tuple[str, str]:
    filename = f"regulatory_note_{topic.lower().replace(' ', '_')}_{year}.md"

    _reg_requirements = {
        "Consumer Duty": [
            "Conduct and document a fair value assessment for all retail products before distribution.",
            "Ensure customer support channels are accessible and capable of handling vulnerability disclosures.",
            "Review all marketing materials for clarity, fairness, and absence of misleading claims.",
        ],
        "Basel IV Capital Requirements": [
            "Recalculate risk-weighted assets using the revised standardised approach by the regulatory deadline.",
            "Update internal capital adequacy assessment process (ICAAP) to reflect new output floor requirements.",
            "Engage the CFO office to model capital impact scenarios under the new framework.",
        ],
        "DORA Operational Resilience": [
            "Register all critical ICT third-party service providers in the group-wide vendor register.",
            "Complete and test a digital operational resilience plan covering all in-scope entities.",
            "Establish an ICT incident classification and reporting process aligned to DORA Article 18.",
        ],
    }
    reqs = _reg_requirements.get(topic, [
        "Review current operating procedures against the updated regulatory framework.",
        "Submit a compliance gap analysis to Group Compliance within 30 days.",
        "Appoint a named compliance owner for all in-scope activities.",
    ])

    content = f"""# Regulatory Compliance Note — {topic}

**Classification:** Internal — Legal & Compliance
**Author:** {fake.name()}, Head of Regulatory Affairs
**Effective Date:** {fake.date_between(start_date=date(year, 1, 1), end_date=date(year, 12, 31))}

## Regulatory Context

Recent guidance from {"the FCA" if random.random() > 0.5 else "the ECB"} and aligned international bodies
requires all business units operating in scope of {topic} to review their current practices and
confirm compliance by the stated effective date.

## Scope

This note applies to:
- All client-facing {random.choice(PRODUCT_LINES)} operations
- Entities regulated in {random.choice(REGIONS)}
- Activities subject to {topic} obligations

## Key Requirements

1. {reqs[0]}
2. {reqs[1]}
3. {reqs[2]}
4. Maintain audit trail for all in-scope transactions for a minimum of **7 years**

## Actions Required

- [ ] Complete gap analysis against current operating procedures
- [ ] Submit compliance attestation to Group Compliance by deadline
- [ ] Update client disclosures where required
- [ ] Train relevant staff on updated obligations

## Contact

For clarification, contact the Regulatory Affairs team at compliance@{fake.domain_name()}.

---
*Failure to comply may result in regulatory sanction. Escalate blockers immediately.*
"""
    return filename, content


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    documents = []

    # Strategy memos
    for pl in PRODUCT_LINES:
        documents.append(strategy_memo(pl, random.choice(REGIONS), "Q3", 2024))

    # Risk assessments — including mandatory Project Apollo
    documents.append(risk_assessment("Project Apollo", "EMEA", 2024))
    documents.append(risk_assessment("Project Horizon", "APAC", 2024))
    documents.append(risk_assessment("Project Meridian", "AMER", 2023))
    documents.append(risk_assessment("Project Catalyst", "EMEA", 2023))

    # Remediation guidance
    for pl in PRODUCT_LINES:
        documents.append(remediation_guidance(pl))

    # Regulatory notes
    documents.append(regulatory_note("Consumer Duty", 2024))
    documents.append(regulatory_note("Basel IV Capital Requirements", 2024))
    documents.append(regulatory_note("DORA Operational Resilience", 2025))

    for filename, content in documents:
        path = OUTPUT_DIR / filename
        path.write_text(content)
        print(f"Wrote → {path.name}")

    print(f"\nGenerated {len(documents)} documents in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
