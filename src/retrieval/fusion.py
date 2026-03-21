from dataclasses import dataclass

from src.retrieval.semantic import SemanticResult
from src.retrieval.structured import StructuredResult

_DEFAULT_MAX_CONTEXT_ITEMS = 8


@dataclass
class ContextItem:
    type: str        # "semantic" or "structured"
    content: str     # chunk text or formatted table rows
    source_ref: str  # source_key (semantic) or generated_sql (structured)
    score: float


@dataclass
class FusedContext:
    items: list[ContextItem]


def fuse(
    semantic_results: list[SemanticResult],
    structured_results: list[StructuredResult],
    max_context_items: int = _DEFAULT_MAX_CONTEXT_ITEMS,
) -> FusedContext:
    items: list[ContextItem] = []

    # De-duplicate semantic chunks by chunk_id — keep highest-scored copy
    best_by_chunk: dict[str, SemanticResult] = {}
    for r in semantic_results:
        if r.chunk_id not in best_by_chunk or r.score > best_by_chunk[r.chunk_id].score:
            best_by_chunk[r.chunk_id] = r

    for r in best_by_chunk.values():
        items.append(ContextItem(
            type="semantic",
            content=r.text,
            source_ref=r.source_key,
            score=r.score,
        ))

    # Structured results with no error get a fixed score of 1.0
    for r in structured_results:
        if r.error:
            continue
        items.append(ContextItem(
            type="structured",
            content=_format_rows(r),
            source_ref=r.generated_sql,
            score=1.0,
        ))

    items.sort(key=lambda x: x.score, reverse=True)
    return FusedContext(items=items[:max_context_items])


def _format_rows(result: StructuredResult) -> str:
    if not result.rows:
        return f"Source: {result.source} — no rows returned."
    header = " | ".join(result.columns)
    rows = "\n".join(" | ".join(str(v) for v in row) for row in result.rows)
    return f"{header}\n{rows}"
