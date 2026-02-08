from server.services.retrieval import filter_relevant_hits


def test_filter_relevant_hits_removes_referrals():
    hits = [
        {"text": "Facility does surgery", "field": "capability"},
        {"text": "We refer surgery cases", "field": "description"},
    ]
    filtered = filter_relevant_hits(hits)
    assert len(filtered) == 1
