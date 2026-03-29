"""
Upload seed documents to GCS (GCP).

Uses Application Default Credentials. Auto-generates documents if missing.
"""

import os
from pathlib import Path

from google.cloud import storage

DOCUMENTS_DIR = Path(__file__).parents[2] / "data" / "seed" / "documents"


def _ensure_documents() -> None:
    if not DOCUMENTS_DIR.exists() or not any(DOCUMENTS_DIR.glob("*.md")):
        print("Documents not found — generating seed documents...")
        from scripts.seed.generate_documents import main
        main()


def load() -> int:
    _ensure_documents()

    project = os.environ["GCP_PROJECT_ID"]
    bucket_name = os.environ["GCS_DOCUMENTS_BUCKET"]

    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)

    documents = list(DOCUMENTS_DIR.glob("*.md"))
    for doc in documents:
        blob = bucket.blob(f"raw/{doc.name}")
        blob.upload_from_filename(str(doc), content_type="text/markdown")
        print(f"Uploaded → {blob.name}")

    print(f"\nUploaded {len(documents)} documents to gs://{bucket_name}/raw/")
    return len(documents)


if __name__ == "__main__":
    load()
