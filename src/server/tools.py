from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from server.data.vector_store import LocalVectorStore
from server.data.warehouse import DuckDbWarehouse
from server.medical_knowledge import missing_equipment


def query_sql(warehouse: DuckDbWarehouse, sql: str) -> List[Tuple]:
    return warehouse.query(sql)


def vector_search(store: LocalVectorStore, embedding: List[float], k: int = 5) -> List[dict]:
    return store.search(embedding, k=k)


def rank_regions_by_gap(region_scores: Dict[str, float]) -> List[Tuple[str, float]]:
    return sorted(region_scores.items(), key=lambda item: item[1])


def flag_facilities_with_missing_equipment(records: Iterable[dict]) -> List[dict]:
    flagged = []
    for row in records:
        procedures = row.get("procedure") or []
        equipment = row.get("equipment") or []
        missing = missing_equipment(procedures, equipment)
        if missing:
            row_copy = dict(row)
            row_copy["missing_equipment"] = missing
            flagged.append(row_copy)
    return flagged
