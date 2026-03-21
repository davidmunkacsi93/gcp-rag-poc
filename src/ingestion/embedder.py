from abc import ABC, abstractmethod
import hashlib
import math

import vertexai
from vertexai.language_models import TextEmbeddingModel


class BaseEmbedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        pass


class StubEmbedder(BaseEmbedder):
    DIMS = 768

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            raw = [digest[i % len(digest)] for i in range(self.DIMS)]
            norm = math.sqrt(sum(v * v for v in raw))
            result.append([v / norm for v in raw])
        return result


class VertexEmbedder(BaseEmbedder):
    _BATCH_SIZE = 250

    def __init__(self, model_name: str, location: str):
        self.model_name = model_name
        self.location = location
        vertexai.init(location=location)
        self._model = TextEmbeddingModel.from_pretrained(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(texts), self._BATCH_SIZE):
            batch = texts[i : i + self._BATCH_SIZE]
            embeddings = self._model.get_embeddings(batch)
            results.extend(e.values for e in embeddings)
        return results


def get_embedder(model: str, location: str = "europe-west1") -> BaseEmbedder:
    if model == "stub":
        return StubEmbedder()
    return VertexEmbedder(model, location)
