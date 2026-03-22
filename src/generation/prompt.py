from src.generation.config import GenerationConfig
from src.retrieval.fusion import FusedContext

_SYSTEM_INSTRUCTION = """\
You are a grounded question-answering assistant.
Answer using ONLY the information provided in the context below.
Cite sources inline using:
  - Semantic sources: [Source: <source_ref>, <section>]
  - Structured sources: [Source: SQL, <source_ref>]
If the context does not contain enough information to answer, say exactly:
"I don't have enough information to answer this question."
Never fabricate information beyond what is in the context.\
"""


def build_prompt(
    query: str,
    context: FusedContext,
    config: GenerationConfig | None = None,
) -> str:
    if config is None:
        config = GenerationConfig()

    budget = config.max_context_tokens
    blocks: list[str] = []
    used_tokens = len(_SYSTEM_INSTRUCTION) // 4

    for i, item in enumerate(context.items, start=1):
        if item.type == "semantic":
            block = (
                f"[{i}] Source: {item.source_ref} (score: {item.score:.3f})\n"
                f"{item.content}"
            )
        else:
            block = (
                f"[{i}] Structured Data — SQL: {item.source_ref}\n"
                f"{item.content}"
            )
        block_tokens = len(block) // 4
        if used_tokens + block_tokens > budget:
            break
        blocks.append(block)
        used_tokens += block_tokens

    context_section = "\n\n".join(blocks)
    return f"{_SYSTEM_INSTRUCTION}\n\n{context_section}\n\nQuestion: {query}"
