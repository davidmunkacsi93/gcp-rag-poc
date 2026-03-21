import os

from google.cloud import aiplatform


class VectorStore:
    def __init__(self, index_name: str, endpoint_name: str, deployed_index_id: str) -> None:
        aiplatform.init(
            project=os.environ["GCP_PROJECT_ID"],
            location=os.environ["VERTEX_AI_LOCATION"],
        )
        self._index = aiplatform.MatchingEngineIndex(index_name=index_name)
        self._deployed_index_id = deployed_index_id

    def upsert(self, datapoints: list[dict]) -> None:
        self._index.upsert_datapoints(datapoints=datapoints)


class MockVectorStore:
    def __init__(self) -> None:
        self.upserted: list[dict] = []

    def upsert(self, datapoints: list[dict]) -> None:
        self.upserted.extend(datapoints)
