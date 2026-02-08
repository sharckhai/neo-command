from server.services.verify import detect_equipment_gaps


def test_detect_equipment_gaps():
    gaps = detect_equipment_gaps(
        procedures=["cataract surgery"],
        equipment=["basic sterilization"],
    )
    assert "cataract surgery" in gaps
