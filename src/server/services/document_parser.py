"""Document parsing and chunking service for RAG pipeline."""
from __future__ import annotations

import os
from typing import Any

from openai import OpenAI


def parse_file(file_path: str) -> list[Any]:
    """Parse a document file into structured elements.

    Supports PDF, DOCX, HTML, TXT, CSV via unstructured.
    """
    from unstructured.partition.auto import partition

    elements = partition(filename=file_path)
    return elements


def chunk_elements(
    elements: list[Any],
    chunk_size: int = 512,
    overlap: int = 128,
) -> list[dict]:
    """Sliding-window chunking by approximate token count.

    Concatenates element texts, then creates overlapping windows.
    Each chunk preserves page/section metadata from the element
    that starts the window.
    """
    # Build a flat list of (text, page, section) from elements
    pieces: list[dict] = []
    for el in elements:
        text = el.text if hasattr(el, "text") else str(el)
        if not text or not text.strip():
            continue
        page = 0
        section = ""
        if hasattr(el, "metadata"):
            page = getattr(el.metadata, "page_number", 0) or 0
            section = getattr(el.metadata, "section", "") or ""
        pieces.append({"text": text, "page": page, "section": section})

    if not pieces:
        return []

    # Concatenate all text with piece boundaries tracked
    full_text = ""
    # Track which piece index each character belongs to
    char_to_piece: list[int] = []
    for i, p in enumerate(pieces):
        if full_text:
            full_text += " "
            char_to_piece.append(i)
        for _ in p["text"]:
            char_to_piece.append(i)
        full_text += p["text"]

    # Approximate tokens as words (split on whitespace)
    words = full_text.split()
    if not words:
        return []

    # Build word-to-char-offset mapping
    word_char_offsets: list[int] = []
    offset = 0
    for word in words:
        idx = full_text.index(word, offset)
        word_char_offsets.append(idx)
        offset = idx + len(word)

    # Sliding window over words
    chunks: list[dict] = []
    step = max(1, chunk_size - overlap)
    chunk_index = 0

    for start in range(0, len(words), step):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])

        # Get metadata from the piece at the start of this window
        char_offset = word_char_offsets[start]
        piece_idx = char_to_piece[min(char_offset, len(char_to_piece) - 1)]
        piece = pieces[piece_idx]

        chunks.append({
            "text": chunk_text,
            "page": piece["page"],
            "section": piece["section"],
            "chunk_index": chunk_index,
        })
        chunk_index += 1

        if end >= len(words):
            break

    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Batch-embed chunks using OpenAI text-embedding-3-small.

    Adds 'embedding' key to each chunk dict. Processes in batches of 100.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings")

    client = OpenAI(api_key=api_key)
    batch_size = 100

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        inputs = [item["text"] for item in batch]
        response = client.embeddings.create(
            model="text-embedding-3-small", input=inputs
        )
        for item, record in zip(batch, response.data):
            item["embedding"] = record.embedding

    return chunks
