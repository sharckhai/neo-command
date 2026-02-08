from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import duckdb

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

    def close(self) -> None:
        self._conn.close()
