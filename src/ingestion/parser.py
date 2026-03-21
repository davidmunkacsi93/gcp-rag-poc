import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedDocument:
    title: str
    doc_type: str
    source_key: str
    sections: list[dict] = field(default_factory=list)


_DOC_TYPE_PREFIXES = [
    "strategy_memo",
    "risk_assessment",
    "remediation",
    "regulatory",
]


def _infer_doc_type(stem: str) -> str:
    for prefix in _DOC_TYPE_PREFIXES:
        if stem.startswith(prefix):
            return prefix
    return "unknown"


def parse_document(raw_text: str, source_key: str) -> ParsedDocument:
    stem = Path(source_key).stem

    title_match = re.search(r"^# (.+)$", raw_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else stem

    doc_type = _infer_doc_type(stem)

    heading_pattern = re.compile(r"^(#{2,3}) (.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(raw_text))

    sections: list[dict] = []

    if matches:
        pre_body = raw_text[: matches[0].start()].strip()
        if pre_body:
            sections.append({"heading": title, "body": pre_body})

        for i, match in enumerate(matches):
            heading = match.group(2).strip()
            body_start = match.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            body = raw_text[body_start:body_end].strip()
            sections.append({"heading": heading, "body": body})
    else:
        sections.append({"heading": title, "body": raw_text.strip()})

    return ParsedDocument(
        title=title,
        doc_type=doc_type,
        source_key=source_key,
        sections=sections,
    )
