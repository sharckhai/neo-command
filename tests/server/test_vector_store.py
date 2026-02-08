import pandas as pd
from server.data.vector_store import LocalVectorStore


def test_local_vector_store_search(tmp_path):
    df = pd.DataFrame([
        {"pk_unique_id": "1", "text": "cataract surgery", "embedding": [0.1] * 1536},
        {"pk_unique_id": "2", "text": "dental cleaning", "embedding": [0.2] * 1536},
    ])
    store = LocalVectorStore(db_path=tmp_path)
    store.upsert(df)
    results = store.search([0.1] * 1536, k=1)
    assert results[0]["pk_unique_id"] == "1"
