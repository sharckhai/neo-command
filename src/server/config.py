from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "output"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    pipeline_target: str = os.getenv("PIPELINE_TARGET", "local")
    entities_path: Path = Path(os.getenv("ENTITIES_PARQUET", OUTPUT_DIR / "step4_entities.parquet"))
    embeddings_path: Path = Path(os.getenv("EMBEDDINGS_PARQUET", OUTPUT_DIR / "step4_embeddings.parquet"))
    lancedb_path: Path = Path(os.getenv("LANCEDB_PATH", OUTPUT_DIR / "lancedb"))

    databricks_host: str | None = os.getenv("DATABRICKS_HOST")
    databricks_token: str | None = os.getenv("DATABRICKS_TOKEN")
    databricks_warehouse_id: str | None = os.getenv("DATABRICKS_WAREHOUSE_ID")
    databricks_catalog: str = os.getenv("DATABRICKS_CATALOG", "hive_metastore")
    databricks_schema: str = os.getenv("DATABRICKS_SCHEMA", "virtuecommand")
    databricks_vector_endpoint: str = os.getenv("DATABRICKS_VECTOR_ENDPOINT", "vs")

    mapbox_token: str | None = os.getenv("MAPBOX_TOKEN")

    def __post_init__(self) -> None:
        target = (self.pipeline_target or "local").lower()
        if target not in {"local", "databricks"}:
            target = "local"
        object.__setattr__(self, "pipeline_target", target)

    def is_databricks(self) -> bool:
        return self.pipeline_target == "databricks"


settings = Settings()
