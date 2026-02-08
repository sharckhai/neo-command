from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from server.config import settings


@dataclass
class DatabricksClient:
    host: str = settings.databricks_host or ""
    token: str = settings.databricks_token or ""
    warehouse_id: str = settings.databricks_warehouse_id or ""
    catalog: str = settings.databricks_catalog
    schema: str = settings.databricks_schema

    def __post_init__(self) -> None:
        if not self.host or not self.token or not self.warehouse_id:
            raise RuntimeError("Missing Databricks environment variables")

    def query(self, sql: str) -> List[Tuple]:
        try:
            from databricks import sql as dbsql
        except Exception as exc:
            raise RuntimeError("databricks-sql-connector is required") from exc

        with dbsql.connect(
            server_hostname=self.host,
            http_path=self.warehouse_id,
            access_token=self.token,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()
