"""
Upload seed documents to the local fake-gcs-server.

Creates the bucket if it does not exist. Uploads all Markdown files from
data/seed/documents/ under the raw/ prefix.

Auto-generates documents if data/seed/documents/ is missing or empty.
"""

import os
from pathlib import Path

from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage

DOCUMENTS_DIR = Path(__file__).parents[2] / "data" / "seed" / "documents"


def _ensure_documents() -> None:
    if not DOCUMENTS_DIR.exists() or not any(DOCUMENTS_DIR.glob("*.md")):
        print("Documents not found — generating seed documents...")
        from scripts.seed.generate_documents import main
        main()


def _client() -> storage.Client:
    return storage.Client(
        project=os.environ.get("GCP_PROJECT_ID", "gcp-rag-poc"),
        credentials=AnonymousCredentials(),
        client_options=ClientOptions(
            api_endpoint=os.environ.get("GCS_EMULATOR_HOST", "http://localhost:4443")
        ),
    )


def load() -> int:
    _ensure_documents()

    client = _client()
    bucket_name = os.environ.get("GCS_DOCUMENTS_BUCKET", "rag-poc-documents-dev")

    bucket = client.lookup_bucket(bucket_name)
    if bucket is None:
        bucket = client.create_bucket(bucket_name)
        print(f"Created bucket: {bucket_name}")

    documents = list(DOCUMENTS_DIR.glob("*.md"))
    for doc in documents:
        blob = bucket.blob(f"raw/{doc.name}")
        blob.upload_from_filename(str(doc), content_type="text/markdown")
        print(f"Uploaded → {blob.name}")

    print(f"\nUploaded {len(documents)} documents to gs://{bucket_name}/raw/")
    return len(documents)


if __name__ == "__main__":
    load()
