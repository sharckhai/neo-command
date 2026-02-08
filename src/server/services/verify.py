from __future__ import annotations

from typing import Dict, Iterable, List

from server.medical_knowledge import missing_equipment


def detect_equipment_gaps(
    procedures: Iterable[str], equipment: Iterable[str]
) -> Dict[str, List[str]]:
    return missing_equipment(procedures, equipment)
