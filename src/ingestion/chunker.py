import re
from dataclasses import dataclass

from src.ingestion.config import IngestionConfig
from src.ingestion.parser import ParsedDocument


@dataclass
class Chunk:
    text: str
    section: str
    chunk_index: int
    token_count: int


def _approximate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[\.\!\?]) ", text)
    return [p.strip() for p in parts if p.strip()]


def _chunks_from_sentences(
    sentences: list[str], chunk_size: int, chunk_overlap: int
) -> list[str]:
    chunks: list[str] = []
    i = 0
    while i < len(sentences):
        accumulated: list[str] = []
        token_count = 0
        j = i
        while j < len(sentences):
            sentence_tokens = _approximate_tokens(sentences[j])
            if token_count + sentence_tokens > chunk_size and accumulated:
                break
            accumulated.append(sentences[j])
            token_count += sentence_tokens
            j += 1

        if not accumulated:
            accumulated.append(sentences[i])
            j = i + 1

        chunks.append(" ".join(accumulated))

        # Only apply overlap when the chunk was full and sentences remain
        if j >= len(sentences):
            break

        overlap_tokens = 0
        backtrack = j - 1
        while backtrack > i and overlap_tokens < chunk_overlap:
            overlap_tokens += _approximate_tokens(sentences[backtrack])
            backtrack -= 1

        next_i = backtrack + 1 if overlap_tokens >= chunk_overlap else j
        if next_i <= i:
            next_i = i + 1
        i = next_i

    return chunks


def chunk_document(parsed_doc: ParsedDocument, config: IngestionConfig) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0

    for section in parsed_doc.sections:
        body = section["body"]
        heading = section["heading"]

        if not body:
            continue

        sentences = _split_sentences(body)
        raw_chunks = _chunks_from_sentences(sentences, config.chunk_size, config.chunk_overlap)

        for raw_chunk in raw_chunks:
            text = f"[Section: {heading}]\n{raw_chunk}"
            chunks.append(
                Chunk(
                    text=text,
                    section=heading,
                    chunk_index=chunk_index,
                    token_count=_approximate_tokens(raw_chunk),
                )
            )
            chunk_index += 1

    return chunks
