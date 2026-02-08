from fastapi.testclient import TestClient
from server.app import app


def test_facilities_endpoint():
    client = TestClient(app)
    res = client.get("/api/facilities")
    assert res.status_code == 200
