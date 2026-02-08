from server.models import ChatRequest, ChatResponse


def test_models_roundtrip():
    req = ChatRequest(message="hello", session_id="abc")
    res = ChatResponse(mode="explore", answer="hi", citations=[])
    assert req.message == "hello"
    assert res.mode == "explore"
