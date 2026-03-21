import os
from dataclasses import dataclass

from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace


@dataclass
class Neighbor:
    id: str
    distance: float


class VectorSearchClient:
    def __init__(self, endpoint_name: str, deployed_index_id: str) -> None:
        aiplatform.init(
            project=os.environ["GCP_PROJECT_ID"],
            location=os.environ["VERTEX_AI_LOCATION"],
        )
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_name
        )
        self._deployed_index_id = deployed_index_id

    def find_neighbors(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        doc_type_filter: str | None = None,
    ) -> list[Neighbor]:
        filter = (
            [Namespace(name="doc_type", allow_tokens=[doc_type_filter])]
            if doc_type_filter
            else None
        )
        response = self._endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[query_embedding],
            num_neighbors=top_k,
            filter=filter,
        )
        neighbors = response[0] if response else []
        return [Neighbor(id=n.id, distance=n.distance) for n in neighbors]


class StubVectorSearchClient:
    """In-memory Vector Search stub for local development and testing.

    Supports upsert (called by ingestion) and find_neighbors (called by
    retrieval), enabling full end-to-end local tests without GCP credentials.
    """

    def __init__(self) -> None:
        self._datapoints: list[dict] = []

    def upsert(self, datapoints: list[dict]) -> None:
        incoming_ids = {dp["datapoint_id"] for dp in datapoints}
        self._datapoints = [
            dp for dp in self._datapoints if dp["datapoint_id"] not in incoming_ids
        ]
        self._datapoints.extend(datapoints)

    def find_neighbors(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        doc_type_filter: str | None = None,
    ) -> list[Neighbor]:
        candidates = self._datapoints
        if doc_type_filter:
            candidates = [
                dp for dp in candidates
                if any(
                    r["namespace"] == "doc_type"
                    and doc_type_filter in r.get("allow_list", [])
                    for r in dp.get("restricts", [])
                )
            ]
        scored = [
            (dp["datapoint_id"], _dot_product(query_embedding, dp["feature_vector"]))
            for dp in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [Neighbor(id=dp_id, distance=score) for dp_id, score in scored[:top_k]]


def get_vector_search_client(
    endpoint_name: str, deployed_index_id: str
) -> VectorSearchClient | StubVectorSearchClient:
    if endpoint_name:
        return VectorSearchClient(endpoint_name, deployed_index_id)
    return StubVectorSearchClient()


def _dot_product(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
