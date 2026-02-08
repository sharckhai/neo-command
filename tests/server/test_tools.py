from server.tools import rank_regions_by_gap


def test_rank_regions_by_gap():
    regions = {"Northern": 10, "Ashanti": 50}
    ranking = rank_regions_by_gap(regions)
    assert ranking[0][0] == "Northern"
