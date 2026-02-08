from server.agents import build_chat_response


def test_must_have_question():
    res = build_chat_response("How many hospitals have cardiology?")
    assert res.mode == "explore"
