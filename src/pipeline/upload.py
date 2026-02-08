from __future__ import annotations

import os
from pathlib import Path
from typing import List

import pandas as pd
from dotenv import load_dotenv

from pipeline.paths import OUTPUT_DIR

INPUT_ENTITIES = OUTPUT_DIR / "step4_entities.parquet"
INPUT_EMBEDDINGS = OUTPUT_DIR / "step4_embeddings.parquet"


def _upload_local(entities: pd.DataFrame, embeddings: pd.DataFrame) -> None:
    try:
        import lancedb
    except Exception as exc:
        raise RuntimeError("lancedb is required for local uploads") from exc

    db_path = OUTPUT_DIR / "lancedb"
    db = lancedb.connect(str(db_path))

    if "facilities" in db.table_names():
        db.drop_table("facilities")
    if "facility_embeddings" in db.table_names():
        db.drop_table("facility_embeddings")

    db.create_table("facilities", entities, mode="overwrite")
    table = db.create_table("facility_embeddings", embeddings, mode="overwrite")
    table.create_index("embedding")


def _upload_databricks(entities: pd.DataFrame, embeddings: pd.DataFrame) -> None:
    raise RuntimeError(
        "Databricks upload is not implemented in this local pipeline. "
        "Use PIPELINE_TARGET=local, or add a Databricks ingestion step that "
        "loads the parquet files from output/ into Delta tables and creates "
        "a Vector Search index."
    )


def upload(
    entities_path: Path = INPUT_ENTITIES,
    embeddings_path: Path = INPUT_EMBEDDINGS,
) -> None:
    load_dotenv()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    entities = pd.read_parquet(entities_path)
    embeddings = pd.read_parquet(embeddings_path)

    target = os.getenv("PIPELINE_TARGET", "local").lower()
    if target == "databricks":
        _upload_databricks(entities, embeddings)
    else:
        _upload_local(entities, embeddings)


if __name__ == "__main__":
    upload()
