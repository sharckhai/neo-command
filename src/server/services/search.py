from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from server.config import settings
from server.data.databricks import DatabricksClient
from server.data.vector_store import LocalVectorStore
from server.data.warehouse import DuckDbWarehouse


def load_entities(parquet_path: Optional[Path] = None) -> pd.DataFrame:
    path = parquet_path or settings.entities_path
    return pd.read_parquet(path)


def facility_count_by_region(parquet_path: Optional[Path] = None) -> Dict[str, int]:
    df = load_entities(parquet_path)
    counts = df["normalized_region"].dropna().value_counts()
    return {key: int(value) for key, value in counts.items()}


def facility_count_by_type(
    parquet_path: Optional[Path] = None, region: Optional[str] = None
) -> Dict[str, int]:
    df = load_entities(parquet_path)
    if region:
        df = df[df["normalized_region"] == region]
    counts = df["facilityTypeId"].dropna().value_counts()
    return {key: int(value) for key, value in counts.items()}


def filter_facilities(
    parquet_path: Optional[Path] = None,
    region: Optional[str] = None,
    facility_type: Optional[str] = None,
    limit: int = 200,
) -> pd.DataFrame:
    df = load_entities(parquet_path)
    if region:
        df = df[df["normalized_region"] == region]
    if facility_type:
        df = df[df["facilityTypeId"].str.lower() == facility_type.lower()]
    return df.head(limit)


def vector_search(embedding: List[float], k: int = 5) -> List[dict]:
    try:
        store = LocalVectorStore()
        return store.search(embedding, k=k)
    except Exception:
        return []


def sql_query(sql: str) -> List[tuple]:
    if settings.is_databricks():
        client = DatabricksClient()
        return client.query(sql)
    warehouse = DuckDbWarehouse()
    return warehouse.query(sql)
