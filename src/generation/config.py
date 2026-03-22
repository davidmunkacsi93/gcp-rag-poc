import os
from dataclasses import dataclass


@dataclass
class GenerationConfig:
    model_name: str = "gemini-2.0-flash-001"
    max_context_tokens: int = 8000
    max_output_tokens: int = 1024
    temperature: float = 0.2
    citation_style: str = "inline"

    @classmethod
    def from_env(cls) -> "GenerationConfig":
        return cls(
            model_name=os.getenv("GENERATION_MODEL", "gemini-2.0-flash-001"),
            max_context_tokens=int(os.getenv("GENERATION_MAX_CONTEXT_TOKENS", "8000")),
            max_output_tokens=int(os.getenv("GENERATION_MAX_OUTPUT_TOKENS", "1024")),
            temperature=float(os.getenv("GENERATION_TEMPERATURE", "0.2")),
            citation_style=os.getenv("GENERATION_CITATION_STYLE", "inline"),
        )
