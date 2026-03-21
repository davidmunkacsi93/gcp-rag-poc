from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


class MetadataStore:
    def __init__(self) -> None:
        self._db = firestore.Client()

    def is_ingested(self, source_key: str) -> bool:
        results = (
            self._db.collection("documents")
            .where(filter=FieldFilter("source_key", "==", source_key))
            .where(filter=FieldFilter("status", "==", "ingested"))
            .limit(1)
            .stream()
        )
        return any(True for _ in results)

    def create_document_record(
        self, doc_id: str, source_key: str, title: str, doc_type: str
    ) -> None:
        self._db.collection("documents").document(doc_id).set(
            {
                "status": "pending",
                "source_key": source_key,
                "title": title,
                "doc_type": doc_type,
            }
        )

    def write_chunks(self, doc_id: str, chunks: list[dict]) -> None:
        batch = self._db.batch()
        for chunk in chunks:
            ref = self._db.collection("chunks").document()
            batch.set(ref, {**chunk, "doc_id": doc_id})
        batch.commit()

    def mark_ingested(self, doc_id: str, chunk_count: int) -> None:
        self._db.collection("documents").document(doc_id).update(
            {
                "status": "ingested",
                "chunk_count": chunk_count,
                "ingested_at": firestore.SERVER_TIMESTAMP,
            }
        )

    def mark_error(self, doc_id: str, error: str) -> None:
        self._db.collection("documents").document(doc_id).update(
            {
                "status": "error",
                "error_message": error,
            }
        )
