from __future__ import annotations

from dataclasses import dataclass

from server.config import settings


@dataclass
class GenieClient:
    host: str | None = settings.databricks_host
    token: str | None = settings.databricks_token
    endpoint: str | None = settings.databricks_genie_endpoint

    def generate_sql(self, prompt: str) -> str:
        if not self.host or not self.token or not self.endpoint:
            raise RuntimeError("Genie is not configured")
        raise RuntimeError("Genie is not configured")
