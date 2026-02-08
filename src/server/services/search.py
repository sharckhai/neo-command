from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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


def count_keyword_by_region(
    keyword: str,
    parquet_path: Optional[Path] = None,
    fields: Iterable[str] = ("procedure", "capability", "equipment", "specialties"),
) -> Dict[str, int]:
    df = load_entities(parquet_path)
    keyword_lower = keyword.lower()
    region_counts: Dict[str, int] = {}
    for _, row in df.iterrows():
        region = row.get("normalized_region")
        if not region:
            continue
        for field in fields:
            values = row.get(field) or []
            combined = " ".join([str(v).lower() for v in values])
            if keyword_lower in combined:
                region_counts[region] = region_counts.get(region, 0) + 1
                break
    return region_counts


def rare_procedures(
    parquet_path: Optional[Path] = None, limit: int = 5
) -> List[Tuple[str, int]]:
    df = load_entities(parquet_path)
    counts: Dict[str, int] = {}
    for _, row in df.iterrows():
        for procedure in row.get("procedure") or []:
            key = str(procedure).strip().lower()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: item[1])
    return ranked[:limit]


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


def filter_facilities_by_keyword(
    keyword: str,
    parquet_path: Optional[Path] = None,
    region: Optional[str] = None,
    limit: int = 200,
    fields: Iterable[str] = ("procedure", "capability", "equipment", "specialties"),
) -> pd.DataFrame:
    df = load_entities(parquet_path)
    if region:
        df = df[df["normalized_region"] == region]
    keyword_lower = keyword.lower()
    matches = []
    for _, row in df.iterrows():
        for field in fields:
            values = row.get(field) or []
            combined = " ".join([str(v).lower() for v in values])
            if keyword_lower in combined:
                matches.append(row)
                break
    if not matches:
        return df.head(0)
    return pd.DataFrame(matches).head(limit)


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
