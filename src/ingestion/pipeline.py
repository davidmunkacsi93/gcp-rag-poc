import sys
from uuid import uuid4

from src.ingestion.chunker import chunk_document
from src.ingestion.config import IngestionConfig
from src.ingestion.embedder import get_embedder
from src.ingestion.metadata import MetadataStore
from src.ingestion.parser import parse_document
from src.ingestion.reader import list_raw_documents, read_document
from src.ingestion.vector_store import MockVectorStore, VectorStore


def run_ingestion(config: IngestionConfig, vector_store=None) -> None:
    if vector_store is None:
        vector_store = VectorStore(config.index_endpoint, config.deployed_index_id)

    metadata = MetadataStore()
    embedder = get_embedder(config.embedding_model, config.vertex_location)

    for doc in list_raw_documents(config):
        source_key = doc["name"]

        if metadata.is_ingested(source_key):
            print(f"Skipping already ingested: {source_key}")
            continue

        doc_id = uuid4().hex

        try:
            raw_text = read_document(config, source_key)
            parsed = parse_document(raw_text, source_key)
            chunks = chunk_document(parsed, config)

            metadata.create_document_record(
                doc_id, source_key, parsed.title, parsed.doc_type
            )

            chunk_texts = [c.text for c in chunks]
            embeddings = embedder.embed(chunk_texts)

            chunk_dicts: list[dict] = []
            datapoints: list[dict] = []

            for chunk, embedding in zip(chunks, embeddings):
                chunk_id = f"{doc_id}_{chunk.chunk_index}"
                chunk_dicts.append(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk.text,
                        "section": chunk.section,
                        "chunk_index": chunk.chunk_index,
                        "token_count": chunk.token_count,
                    }
                )
                datapoints.append(
                    {
                        "datapoint_id": chunk_id,
                        "feature_vector": embedding,
                        "restricts": [
                            {"namespace": "doc_id", "allow_list": [doc_id]},
                            {"namespace": "doc_type", "allow_list": [parsed.doc_type]},
                        ],
                    }
                )

            metadata.write_chunks(doc_id, chunk_dicts)
            vector_store.upsert(datapoints)
            metadata.mark_ingested(doc_id, len(chunks))
            print(f"Ingested: {source_key} ({len(chunks)} chunks)")

        except Exception as e:
            metadata.mark_error(doc_id, str(e))
            print(f"Error ingesting {source_key}: {e}")
            continue


if __name__ == "__main__":
    config = IngestionConfig.from_env()
    store = MockVectorStore() if "--dry-run" in sys.argv else None
    run_ingestion(config, vector_store=store)
