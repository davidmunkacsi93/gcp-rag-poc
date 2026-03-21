import re
from dataclasses import dataclass

_METRIC_TERMS = frozenset({
    "revenue", "margin", "growth", "headcount", "quarter", "region",
    "yoy", "profit", "cost", "kpi", "performance", "metric",
    "financial", "underperform", "overperform", "budget", "forecast",
    "exposure", "loss", "gain",
})

_DOCUMENT_TERMS = frozenset({
    "document", "report", "guidance", "policy", "risk", "remediation",
    "regulatory", "strategy", "memo", "assessment", "compliance",
    "due", "diligence", "finding", "note",
})

# Ordered: first match wins
_DOC_TYPE_HINTS: list[tuple[str, str]] = [
    ("remediation", "remediation"),
    ("regulatory", "regulatory"),
    ("compliance", "regulatory"),
    ("risk", "risk_assessment"),
    ("diligence", "risk_assessment"),
    ("strategy", "strategy_memo"),
    ("memo", "strategy_memo"),
]


@dataclass
class RoutingDecision:
    semantic: bool
    structured_bigquery: bool
    structured_cloudsql: bool
    doc_type_filter: str | None


def route(query: str) -> RoutingDecision:
    lower = query.lower()
    words = set(re.findall(r"\w+", lower))

    has_metric = bool(words & _METRIC_TERMS)
    has_document = bool(words & _DOCUMENT_TERMS)

    # Safe default: activate both paths when signal is ambiguous
    if not has_metric and not has_document:
        has_metric = True
        has_document = True

    doc_type_filter = None
    if has_document:
        for term, doc_type in _DOC_TYPE_HINTS:
            if term in lower:
                doc_type_filter = doc_type
                break

    return RoutingDecision(
        semantic=has_document,
        structured_bigquery=has_metric,
        structured_cloudsql=has_metric,
        doc_type_filter=doc_type_filter,
    )
