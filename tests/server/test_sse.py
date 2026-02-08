from fastapi.testclient import TestClient
from server.app import app


def test_sse_endpoint():
    client = TestClient(app)
    res = client.post("/api/chat", json={"message": "hi", "session_id": "t1"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
