from server.agents import classify_mode


def test_classify_mode_rules():
    assert classify_mode("Which facilities claim surgery but lack equipment?") == "verify"
    assert classify_mode("Where should we deploy?") == "plan"
