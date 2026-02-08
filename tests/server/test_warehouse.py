import pandas as pd
from server.data.warehouse import DuckDbWarehouse


def test_duckdb_query(tmp_path):
    df = pd.DataFrame([
        {"pk_unique_id": "1", "name": "Alpha", "normalized_region": "Northern"},
        {"pk_unique_id": "2", "name": "Beta", "normalized_region": "Northern"},
    ])
    parquet = tmp_path / "entities.parquet"
    df.to_parquet(parquet, index=False)

    warehouse = DuckDbWarehouse(entities_path=parquet)
    result = warehouse.query("SELECT COUNT(*) as c FROM facilities")
    assert result[0][0] == 2
