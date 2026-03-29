import logging
import os

from src.ingestion.embedder import get_embedder
from src.retrieval.fusion import FusedContext, fuse
from src.retrieval.router import route
from src.retrieval.semantic import semantic_retrieve
from src.retrieval.structured import query_bigquery, query_cloudsql
from src.retrieval.vector_store import get_vector_search_client

logger = logging.getLogger(__name__)


def retrieve(query: str) -> FusedContext:
    decision = route(query)
    logger.debug("Routing decision: semantic=%s bq=%s cloudsql=%s doc_type_filter=%s",
                 decision.semantic, decision.structured_bigquery, decision.structured_cloudsql, decision.doc_type_filter)

    vector_client = get_vector_search_client(
        endpoint_name=os.getenv("VERTEX_AI_INDEX_ENDPOINT", ""),
        deployed_index_id=os.getenv("VERTEX_AI_DEPLOYED_INDEX_ID", ""),
    )
    embedder = get_embedder(
        model=os.getenv("EMBEDDING_MODEL", "stub"),
        location=os.getenv("VERTEX_AI_LOCATION", "europe-west1"),
    )

    semantic_results = []
    structured_results = []

    if decision.semantic:
        semantic_results = semantic_retrieve(
            query,
            vector_client=vector_client,
            embedder=embedder,
            top_k=15,
            doc_type_filter=decision.doc_type_filter,
        )

    if decision.structured_bigquery:
        structured_results.append(query_bigquery(query))

    if decision.structured_cloudsql:
        structured_results.append(query_cloudsql(query))

    fused = fuse(semantic_results, structured_results)
    logger.debug("fuse returned %d context items", len(fused.items))
    return fused
