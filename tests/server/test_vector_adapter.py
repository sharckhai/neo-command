from server.data.vector_search import VectorSearchClient


def test_vector_search_falls_back_to_empty():
    client = VectorSearchClient()
    results = client.search([0.0, 0.0], k=3)
    assert results == []
