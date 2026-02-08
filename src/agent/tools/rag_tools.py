"""RAG tools: ingest, query, and list uploaded documents."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from agents import function_tool

from server.data.vector_store import LocalVectorStore
from server.services.document_parser import chunk_elements, embed_chunks, parse_file

_TABLE = "document_chunks"


def _embed_query(query: str) -> list[float] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model="text-embedding-3-small", input=[query])
    if not response.data:
        return None
    return response.data[0].embedding


def make_rag_tools() -> list:
    """Create RAG tools (no graph dependency)."""

    @function_tool
    def ingest_document(file_path: str, source_label: str = "") -> str:
        """Parse, chunk, embed, and index a document file into the vector store.

        Supports PDF, DOCX, HTML, TXT, CSV files.

        Args:
            file_path: Path to the file to ingest.
            source_label: Human-readable label for this document (defaults to filename).
        """
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"error": f"File not found: {file_path}"})

        label = source_label or path.name

        # Parse
        elements = parse_file(file_path)
        if not elements:
            return json.dumps({"error": "No content extracted from file"})

        # Chunk
        chunks = chunk_elements(elements)
        if not chunks:
            return json.dumps({"error": "No chunks produced from file"})

        # Add metadata
        for chunk in chunks:
            chunk["source_label"] = label
            chunk["file_path"] = str(path.resolve())

        # Embed
        embed_chunks(chunks)

        # Upsert into LanceDB
        df = pd.DataFrame(chunks)
        store = LocalVectorStore(table_name=_TABLE)
        store.upsert(df)

        return json.dumps({
            "status": "ok",
            "message": f"Indexed {len(chunks)} chunks from {label}",
            "chunks": len(chunks),
            "source_label": label,
        })

    @function_tool
    def query_documents(
        question: str, k: int = 5, source_filter: str | None = None
    ) -> str:
        """Search indexed documents by semantic similarity.

        Args:
            question: Natural language question to search for.
            k: Number of results to return (default 5).
            source_filter: Optional source_label to restrict search to one document.
        """
        embedding = _embed_query(question)
        if embedding is None:
            return json.dumps({"error": "Missing OPENAI_API_KEY for embeddings"})

        store = LocalVectorStore(table_name=_TABLE)
        results = store.search(embedding, k=k * 3 if source_filter else k)

        # Post-filter by source_label if specified
        if source_filter:
            results = [
                r for r in results if r.get("source_label") == source_filter
            ][:k]

        # Clean up results for output
        output = []
        for r in results[:k]:
            output.append({
                "text": r.get("text", ""),
                "source_label": r.get("source_label", ""),
                "page": r.get("page", 0),
                "chunk_index": r.get("chunk_index", 0),
                "score": r.get("_distance", 0),
            })

        return json.dumps(output, default=str)

    @function_tool
    def list_documents() -> str:
        """List all ingested document source labels.

        Returns the distinct source labels of all documents that have been
        indexed into the vector store.
        """
        store = LocalVectorStore(table_name=_TABLE)
        db = store._connect()
        tables = store._list_tables(db)

        if _TABLE not in tables:
            return json.dumps([])

        table = db.open_table(_TABLE)
        df = table.to_pandas()
        labels = sorted(df["source_label"].unique().tolist())
        return json.dumps(labels)

    return [ingest_document, query_documents, list_documents]
