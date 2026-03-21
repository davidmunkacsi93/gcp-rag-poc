import os
from dataclasses import dataclass


@dataclass
class IngestionConfig:
    gcs_bucket: str
    raw_prefix: str
    processed_prefix: str
    chunk_size: int
    chunk_overlap: int
    embedding_model: str
    vertex_location: str
    index_endpoint: str
    deployed_index_id: str

    @classmethod
    def from_env(cls) -> "IngestionConfig":
        return cls(
            gcs_bucket=os.getenv("GCS_DOCUMENTS_BUCKET", ""),
            raw_prefix=os.getenv("GCS_RAW_PREFIX", "raw/"),
            processed_prefix=os.getenv("GCS_PROCESSED_PREFIX", "processed/"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            embedding_model=os.getenv("EMBEDDING_MODEL", "stub"),
            vertex_location=os.getenv("VERTEX_AI_LOCATION", "europe-west1"),
            index_endpoint=os.getenv("VERTEX_AI_INDEX_ENDPOINT", ""),
            deployed_index_id=os.getenv("VERTEX_AI_DEPLOYED_INDEX_ID", ""),
        )
