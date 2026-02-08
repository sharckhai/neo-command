from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import duckdb
import pandas as pd

from server.config import settings


@dataclass
class DuckDbWarehouse:
    entities_path: Path = settings.entities_path

    def __post_init__(self) -> None:
        self._conn = duckdb.connect(database=":memory:")
        self._conn.execute(
            "CREATE VIEW facilities AS SELECT * FROM read_parquet(?)",
            [str(self.entities_path)],
        )

    def query(self, sql: str) -> List[Tuple]:
        results = self._conn.execute(sql).fetchall()
        return list(results)

    def query_df(self, sql: str) -> pd.DataFrame:
        return self._conn.execute(sql).df()

    def close(self) -> None:
        self._conn.close()
