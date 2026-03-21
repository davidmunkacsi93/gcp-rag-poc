import os

import pytest
from google.cloud import firestore


@pytest.fixture(scope="module", autouse=True)
def clear_firestore_collections():
    """Delete all documents and chunks from Firestore before each test module.

    Only runs when FIRESTORE_EMULATOR_HOST is set (i.e. against the local
    emulator) to avoid accidentally wiping real GCP data during gcp-marked tests.
    """
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        yield
        return

    db = firestore.Client()
    for collection in ("documents", "chunks"):
        for doc in db.collection(collection).stream():
            doc.reference.delete()

    yield
