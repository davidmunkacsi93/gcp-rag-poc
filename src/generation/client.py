import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import vertexai
from vertexai.generative_models import GenerationConfig as VertexGenerationConfig
from vertexai.generative_models import GenerativeModel

from src.generation.config import GenerationConfig


@dataclass
class RawGenerationResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int


class BaseGenerationClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, config: GenerationConfig) -> RawGenerationResponse:
        pass


class VertexGenerationClient(BaseGenerationClient):
    def __init__(self) -> None:
        vertexai.init(
            project=os.environ["GCP_PROJECT_ID"],
            location=os.environ["VERTEX_AI_LOCATION"],
        )

    def generate(self, prompt: str, config: GenerationConfig) -> RawGenerationResponse:
        model = GenerativeModel(config.model_name)
        response = model.generate_content(
            prompt,
            generation_config=VertexGenerationConfig(
                max_output_tokens=config.max_output_tokens,
                temperature=config.temperature,
            ),
        )
        usage = response.usage_metadata
        return RawGenerationResponse(
            text=response.text,
            prompt_tokens=usage.prompt_token_count,
            completion_tokens=usage.candidates_token_count,
        )


class StubGenerationClient(BaseGenerationClient):
    def generate(self, prompt: str, config: GenerationConfig) -> RawGenerationResponse:
        text = (
            "Stub response — generation service is running in stub mode. "
            "Set `GENERATION_STUB=false` to use Gemini. "
            "[Source: stub_source, stub_section]"
        )
        return RawGenerationResponse(
            text=text,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(text) // 4,
        )


def get_generation_client() -> BaseGenerationClient:
    if os.environ.get("GENERATION_STUB", "").lower() == "true":
        return StubGenerationClient()
    return VertexGenerationClient()
