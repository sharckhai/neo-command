from server.services.verify import detect_equipment_gaps, infer_unrealistic_breadth


def test_detect_equipment_gaps():
    gaps = detect_equipment_gaps(
        procedures=["cataract surgery"],
        equipment=["basic sterilization"],
    )
    assert "cataract surgery" in gaps


def test_infer_unrealistic_breadth():
    flags = infer_unrealistic_breadth(
        procedures=["cardiac surgery", "neurosurgery", "orthopedic surgery", "transplant", "dialysis", "oncology"],
        capacity=5,
    )
    assert "breadth_depth_mismatch" in flags
