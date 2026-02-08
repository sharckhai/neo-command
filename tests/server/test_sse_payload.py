from server.app import _format_sse_event


def test_format_sse_event():
    data = _format_sse_event({"type": "token", "text": "hi"})
    assert data.startswith("data:")
