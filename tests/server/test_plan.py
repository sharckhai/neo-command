from server.services.plan import rank_regions_by_facility_density


def test_rank_regions_by_facility_density():
    ranking = rank_regions_by_facility_density({"Northern": 10, "Ashanti": 50})
    assert ranking[0][0] == "Northern"
