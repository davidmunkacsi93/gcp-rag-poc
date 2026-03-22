from dataclasses import dataclass

from src.generation.citations import Citation, extract_citations
from src.generation.client import get_generation_client
from src.generation.config import GenerationConfig
from src.generation.prompt import build_prompt
from src.retrieval.fusion import FusedContext


@dataclass
class GenerationResult:
    answer: str
    citations: list[Citation]
    model: str
    prompt_tokens: int


def generate(query: str, context: FusedContext) -> GenerationResult:
    config = GenerationConfig.from_env()
    prompt = build_prompt(query, context, config)
    response = get_generation_client().generate(prompt, config)
    citations = extract_citations(response.text, context)
    return GenerationResult(
        answer=response.text,
        citations=citations,
        model=config.model_name,
        prompt_tokens=response.prompt_tokens,
    )
