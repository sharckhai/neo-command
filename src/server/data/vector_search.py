from __future__ import annotations

from dataclasses import dataclass
from typing import List

from server.config import settings


@dataclass
class VectorSearchClient:
    host: str | None = settings.databricks_host
    token: str | None = settings.databricks_token
    endpoint: str = settings.databricks_vector_endpoint

    def search(self, embedding: List[float], k: int = 5) -> List[dict]:
        if not self.host or not self.token:
            return []
        return []
