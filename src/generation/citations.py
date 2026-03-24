import re
from dataclasses import dataclass

from src.retrieval.fusion import FusedContext

_CITATION_RE = re.compile(r"\[Source:\s*([^,\]]+),\s*([^\]]+)\]")


@dataclass
class Citation:
    source_key: str
    doc_id: str
    section: str
    type: str
    generated_sql: str


def extract_citations(answer: str, context: FusedContext) -> list[Citation]:
    seen: set[tuple[str, str]] = set()
    citations: list[Citation] = []

    for match in _CITATION_RE.finditer(answer):
        ref = match.group(1).strip()
        detail = match.group(2).strip()

        if ref == "SQL":
            item = next(
                (c for c in context.items if c.type == "structured"), None
            )
            citation = Citation(
                source_key="SQL",
                doc_id="",
                section="N/A",
                type="structured",
                generated_sql=item.source_ref if item else "",
            )
        else:
            citation = Citation(
                source_key=ref,
                doc_id="",
                section=detail,
                type="semantic",
                generated_sql="",
            )

        key = (citation.source_key, citation.section)
        if key not in seen:
            seen.add(key)
            citations.append(citation)

    return citations
