import os

from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage

from src.ingestion.config import IngestionConfig


def _client() -> storage.Client:
    emulator_host = os.getenv("GCS_EMULATOR_HOST")
    if emulator_host:
        return storage.Client(
            project=os.getenv("GCP_PROJECT_ID", "gcp-rag-poc"),
            credentials=AnonymousCredentials(),
            client_options=ClientOptions(api_endpoint=emulator_host),
        )
    return storage.Client()


def list_raw_documents(config: IngestionConfig) -> list[dict]:
    client = _client()
    bucket = client.bucket(config.gcs_bucket)
    blobs = client.list_blobs(bucket, prefix=config.raw_prefix)
    return [
        {"name": blob.name, "size": blob.size, "updated": blob.updated}
        for blob in blobs
    ]


def read_document(config: IngestionConfig, key: str) -> str:
    client = _client()
    bucket = client.bucket(config.gcs_bucket)
    blob = bucket.blob(key)
    return blob.download_as_text(encoding="utf-8")
