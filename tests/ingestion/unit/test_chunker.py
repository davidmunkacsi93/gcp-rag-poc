"""Tests for the chunker module."""

import pytest

from src.ingestion.chunker import chunk_document, _approximate_tokens
from src.ingestion.config import IngestionConfig
from src.ingestion.parser import ParsedDocument


SENTENCE = (
    "This is a sentence that contains enough words to contribute meaningfully to the token count. "
)

LONG_BODY = SENTENCE * 40


@pytest.fixture
def config():
    return IngestionConfig(
        gcs_bucket="",
        raw_prefix="raw/",
        processed_prefix="processed/",
        chunk_size=100,
        chunk_overlap=20,
        embedding_model="stub",
        vertex_location="europe-west1",
        index_endpoint="",
        deployed_index_id="",
    )


@pytest.fixture
def multi_section_doc():
    return ParsedDocument(
        title="Test Document",
        doc_type="strategy_memo",
        source_key="raw/strategy_memo_test.md",
        sections=[
            {"heading": "Introduction", "body": LONG_BODY},
            {"heading": "Analysis", "body": LONG_BODY},
        ],
    )


def test_chunk_document_returns_non_empty_list_for_document_with_content(multi_section_doc, config):
    chunks = chunk_document(multi_section_doc, config)
    assert len(chunks) > 0


def test_chunk_document_returns_empty_list_for_document_with_no_sections(config):
    doc = ParsedDocument(
        title="Empty",
        doc_type="unknown",
        source_key="raw/empty.md",
        sections=[],
    )
    chunks = chunk_document(doc, config)
    assert chunks == []


def test_chunk_document_each_chunk_has_non_empty_text(multi_section_doc, config):
    chunks = chunk_document(multi_section_doc, config)
    for chunk in chunks:
        assert chunk.text.strip() != ""


def test_chunk_document_each_chunk_text_is_prefixed_with_section(multi_section_doc, config):
    chunks = chunk_document(multi_section_doc, config)
    for chunk in chunks:
        assert chunk.text.startswith("[Section: ")


def test_chunk_document_chunk_index_is_sequential_across_sections(multi_section_doc, config):
    chunks = chunk_document(multi_section_doc, config)
    for expected_index, chunk in enumerate(chunks):
        assert chunk.chunk_index == expected_index


def test_chunk_document_respects_chunk_size(multi_section_doc, config):
    max_allowed = config.chunk_size + _approximate_tokens(SENTENCE)
    chunks = chunk_document(multi_section_doc, config)
    for chunk in chunks:
        assert chunk.token_count <= max_allowed


def test_chunk_document_produces_overlap_between_consecutive_chunks(config):
    sentences = [f"Sentence number {i} provides unique content for testing overlap behaviour." for i in range(20)]
    body = " ".join(sentences)
    doc = ParsedDocument(
        title="Overlap Test",
        doc_type="strategy_memo",
        source_key="raw/strategy_memo_overlap.md",
        sections=[{"heading": "Main", "body": body}],
    )
    chunks = chunk_document(doc, config)
    assert len(chunks) >= 2, "need at least 2 chunks to verify overlap"
    for i in range(len(chunks) - 1):
        last_words_of_chunk = chunks[i].text.split()[-5:]
        next_chunk_text = chunks[i + 1].text
        assert any(word in next_chunk_text for word in last_words_of_chunk), (
            f"No overlap detected between chunk {i} and chunk {i + 1}"
        )


def test_chunk_document_returns_empty_list_when_all_sections_have_empty_body(config):
    doc = ParsedDocument(
        title="All Empty",
        doc_type="unknown",
        source_key="raw/unknown_empty.md",
        sections=[
            {"heading": "Section A", "body": ""},
            {"heading": "Section B", "body": ""},
        ],
    )
    chunks = chunk_document(doc, config)
    assert chunks == []
