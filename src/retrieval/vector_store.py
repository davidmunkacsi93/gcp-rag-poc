import logging
import os
from dataclasses import dataclass

import google.auth
import google.auth.transport.requests
import requests as http_requests
from google.cloud import aiplatform

logger = logging.getLogger(__name__)


@dataclass
class Neighbor:
    id: str
    distance: float


class VectorSearchClient:
    """Uses raw HTTP for find_neighbors to avoid gapic REST transport state
    pollution ($alt=json;enum-encoding=int) that occurs after vertexai.init()
    is called (e.g. from the structured retriever), which causes the SDK's
    MatchingEngineIndexEndpoint.find_neighbors to fail on the vdb.vertexai.goog
    match endpoint with a 400 error on all subsequent calls."""

    def __init__(self, endpoint_name: str, deployed_index_id: str) -> None:
        self._deployed_index_id = deployed_index_id
        aiplatform.init(
            project=os.environ["GCP_PROJECT_ID"],
            location=os.environ["VERTEX_AI_LOCATION"],
        )
        sdk_ep = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=endpoint_name
        )
        self._resource_name = sdk_ep.resource_name
        self._domain = sdk_ep.public_endpoint_domain_name

    def find_neighbors(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        doc_type_filter: str | None = None,
    ) -> list[Neighbor]:
        credentials, _ = google.auth.default()
        credentials.refresh(google.auth.transport.requests.Request())

        url = f"https://{self._domain}/v1beta1/{self._resource_name}:findNeighbors"
        payload = {
            "deployed_index_id": self._deployed_index_id,
            "queries": [
                {
                    "datapoint": {"feature_vector": query_embedding},
                    "neighbor_count": top_k,
                }
            ],
        }
        resp = http_requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {credentials.token}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_neighbors = data.get("nearestNeighbors", [{}])[0].get("neighbors", [])
        return [
            Neighbor(
                id=n["datapoint"]["datapointId"],
                distance=n.get("distance", 0.0),
            )
            for n in raw_neighbors
        ]


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
