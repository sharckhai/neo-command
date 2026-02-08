from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from rich.progress import Progress

from pipeline.paths import OUTPUT_DIR

INPUT_PARQUET = OUTPUT_DIR / "step3_fingerprinted.parquet"
OUTPUT_EMBEDDINGS = OUTPUT_DIR / "step4_embeddings.parquet"
OUTPUT_ENTITIES = OUTPUT_DIR / "step4_entities.parquet"


def _build_chunks(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    name = row.get("name") or "Unknown"
    city = row.get("address_city") or "Unknown City"
    facility_type = row.get("facilityTypeId") or "facility"

    def add_chunk(field: str, content: str) -> None:
        if not content:
            return
        text = f"{name} ({facility_type} in {city}): {field}: {content}"
        chunks.append({
            "pk_unique_id": row.get("pk_unique_id"),
            "name": name,
            "field": field,
            "text": text,
            "facilityTypeId": row.get("facilityTypeId"),
            "region": row.get("normalized_region"),
            "city": row.get("address_city"),
            "specialties": row.get("specialties") or [],
            "confidence": row.get("confidence"),
        })

    for field in ["procedure", "equipment", "capability"]:
        items = row.get(field) or []
        if items:
            add_chunk(field, "; ".join(items))

    description = row.get("description") or ""
    if description:
        add_chunk("description", description)

    return chunks


def embed(input_path: Path = INPUT_PARQUET) -> List[Path]:
    load_dotenv()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(input_path)
    records = df.to_dict("records")

    chunks: List[Dict[str, Any]] = []
    for row in records:
        chunks.extend(_build_chunks(row))

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings")

    client = OpenAI(api_key=api_key)

    embeddings: List[List[float]] = []
    batch_size = 100

    with Progress() as progress:
        task = progress.add_task("Embedding", total=len(chunks))
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            inputs = [item["text"] for item in batch]
            response = client.embeddings.create(model="text-embedding-3-small", input=inputs)
            for item, record in zip(batch, response.data):
                item["embedding"] = record.embedding
            embeddings.extend(batch)
            progress.advance(task, advance=len(batch))

    embeddings_df = pd.DataFrame(embeddings)
    embeddings_df.to_parquet(OUTPUT_EMBEDDINGS, index=False)

    entities_df = pd.DataFrame(records)
    entities_df.to_parquet(OUTPUT_ENTITIES, index=False)

    return [OUTPUT_ENTITIES, OUTPUT_EMBEDDINGS]


if __name__ == "__main__":
    embed()
