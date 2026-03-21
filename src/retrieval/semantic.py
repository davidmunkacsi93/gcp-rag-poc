import logging
from dataclasses import dataclass

from google.cloud import firestore

logger = logging.getLogger(__name__)
from google.cloud.firestore_v1.base_query import FieldFilter

from src.ingestion.embedder import BaseEmbedder
from src.retrieval.vector_store import StubVectorSearchClient, VectorSearchClient


@dataclass
class SemanticResult:
    chunk_id: str
    text: str
    section: str
    doc_id: str
    source_key: str
    score: float


def semantic_retrieve(
    query: str,
    vector_client: VectorSearchClient | StubVectorSearchClient,
    embedder: BaseEmbedder,
    top_k: int = 5,
    doc_type_filter: str | None = None,
) -> list[SemanticResult]:
    embedding = embedder.embed([query])[0]
    neighbors = vector_client.find_neighbors(
        query_embedding=embedding,
        top_k=top_k,
        doc_type_filter=doc_type_filter,
    )
    logger.debug("find_neighbors returned %d neighbors", len(neighbors))

    db = firestore.Client()
    results = []

    for neighbor in neighbors:
        chunk_docs = list(
            db.collection("chunks")
            .where(filter=FieldFilter("chunk_id", "==", neighbor.id))
            .limit(1)
            .stream()
        )
        if not chunk_docs:
            logger.warning("No Firestore chunk found for neighbor id=%s", neighbor.id)
            continue

        chunk = chunk_docs[0].to_dict()
        doc_id = chunk["doc_id"]
        doc_snapshot = db.collection("documents").document(doc_id).get()
        source_key = (doc_snapshot.to_dict() or {}).get("source_key", "")
        logger.debug("Resolved chunk_id=%s doc_id=%s source_key=%s score=%f", neighbor.id, doc_id, source_key, neighbor.distance)

        results.append(SemanticResult(
            chunk_id=neighbor.id,
            text=chunk.get("text", ""),
            section=chunk.get("section", ""),
            doc_id=doc_id,
            source_key=source_key,
            score=neighbor.distance,
        ))

    logger.debug("semantic_retrieve returning %d results", len(results))
    return results
