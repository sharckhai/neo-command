from server.agents import build_chat_response


def test_explore_response_returns_facilities():
    res = build_chat_response("How many hospitals in Northern Region?")
    assert res.mode == "explore"
