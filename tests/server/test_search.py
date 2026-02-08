import pandas as pd
from server.services.search import facility_count_by_region


def test_facility_count_by_region(tmp_path):
    df = pd.DataFrame([
        {"pk_unique_id": "1", "normalized_region": "Northern"},
        {"pk_unique_id": "2", "normalized_region": "Northern"},
        {"pk_unique_id": "3", "normalized_region": "Ashanti"},
    ])
    parquet = tmp_path / "entities.parquet"
    df.to_parquet(parquet, index=False)

    counts = facility_count_by_region(parquet)
    assert counts["Northern"] == 2
