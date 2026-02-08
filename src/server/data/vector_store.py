from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd

from server.config import settings


@dataclass
class LocalVectorStore:
    db_path: Path = settings.lancedb_path
    table_name: str = "facility_embeddings"

    def _connect(self):
        try:
            import lancedb
        except Exception as exc:
            raise RuntimeError("lancedb is required for LocalVectorStore") from exc
        return lancedb.connect(str(self.db_path))

    def _list_tables(self, db) -> List[str]:
        tables = db.list_tables()
        if isinstance(tables, list):
            return tables
        if hasattr(tables, "tables"):
            return list(tables.tables)
        try:
            return list(tables)
        except TypeError:
            return []

    def upsert(self, df: pd.DataFrame) -> None:
        db = self._connect()
        tables = self._list_tables(db)
        if self.table_name in tables:
            table = db.open_table(self.table_name)
            table.add(df)
        else:
            db.create_table(self.table_name, df, mode="overwrite")

    def search(self, embedding: List[float], k: int = 5) -> List[dict]:
        db = self._connect()
        tables = self._list_tables(db)
        if self.table_name not in tables:
            return []
        table = db.open_table(self.table_name)
        results = table.search(embedding).limit(k).to_list()
        return results
