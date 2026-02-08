from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

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

    def upsert(self, df: pd.DataFrame) -> None:
        db = self._connect()
        if self.table_name in db.table_names():
            table = db.open_table(self.table_name)
            table.add(df)
        else:
            db.create_table(self.table_name, df, mode="overwrite")

    def search(self, embedding: List[float], k: int = 5) -> List[dict]:
        db = self._connect()
        if self.table_name not in db.table_names():
            return []
        table = db.open_table(self.table_name)
        results = table.search(embedding).limit(k).to_list()
        return results
