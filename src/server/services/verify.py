from __future__ import annotations

from typing import Dict, Iterable, List

from server.medical_knowledge import (
    contains_aspirational_language,
    contains_referral_language,
    missing_equipment,
)


def detect_equipment_gaps(
    procedures: Iterable[str], equipment: Iterable[str]
) -> Dict[str, List[str]]:
    return missing_equipment(procedures, equipment)


def infer_unrealistic_breadth(
    procedures: Iterable[str], capacity: int | None
) -> List[str]:
    procedures_list = [p for p in procedures if p]
    if capacity is None or capacity <= 0:
        return []
    if len(procedures_list) >= 6 and capacity <= 10:
        return ["breadth_depth_mismatch"]
    return []


def detect_referral_or_aspirational(text: str) -> List[str]:
    flags: List[str] = []
    if contains_referral_language(text):
        flags.append("referral_only")
    if contains_aspirational_language(text):
        flags.append("aspirational_language")
    return flags
