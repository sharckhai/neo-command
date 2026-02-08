from server.medical_knowledge import required_equipment_for


def test_required_equipment():
    req = required_equipment_for("cataract surgery")
    assert "microscope" in " ".join(req).lower()
