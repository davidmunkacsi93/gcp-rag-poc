from google.cloud import aiplatform


class VectorStore:
    def __init__(self, endpoint_name: str, deployed_index_id: str) -> None:
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_name
        )
        self._deployed_index_id = deployed_index_id

    def upsert(self, datapoints: list[dict]) -> None:
        self._endpoint.upsert_datapoints(datapoints=datapoints)


class MockVectorStore:
    def __init__(self) -> None:
        self.upserted: list[dict] = []

    def upsert(self, datapoints: list[dict]) -> None:
        self.upserted.extend(datapoints)
