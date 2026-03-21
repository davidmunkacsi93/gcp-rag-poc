from abc import ABC, abstractmethod
import hashlib
import math


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
    def __init__(self, model_name: str, location: str):
        self.model_name = model_name
        self.location = location

    def embed(self, texts: list[str]) -> list[list[float]]:
        # TODO: implement using Vertex AI text embedding API in Stream C
        raise NotImplementedError


def get_embedder(model: str, location: str = "europe-west1") -> BaseEmbedder:
    if model == "stub":
        return StubEmbedder()
    return VertexEmbedder(model, location)
