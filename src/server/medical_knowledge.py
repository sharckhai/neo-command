from __future__ import annotations

from typing import Dict, Iterable, List

EQUIPMENT_REQUIREMENTS: Dict[str, List[str]] = {
    "cataract": ["ophthalmic microscope", "phacoemulsification", "sterilization"],
    "surgery": ["operating theatre", "anesthesia", "sterilization"],
    "cesarean": ["operating theatre", "anesthesia", "sterilization"],
    "orthopedic": ["x-ray", "sterilization"],
    "dialysis": ["dialysis machine", "water treatment"],
    "icu": ["ventilator", "patient monitor"],
}

ASPIRATIONAL_KEYWORDS = [
    "plan to",
    "planning to",
    "aim to",
    "hope to",
    "future",
    "coming soon",
    "will offer",
]

REFERRAL_KEYWORDS = [
    "refer",
    "referral",
    "referred",
    "transfer",
    "transferred",
    "send patients",
]


def required_equipment_for(procedure: str) -> List[str]:
    text = procedure.lower()
    for key, items in EQUIPMENT_REQUIREMENTS.items():
        if key in text:
            return items
    return []


def missing_equipment(
    procedures: Iterable[str], equipment: Iterable[str]
) -> Dict[str, List[str]]:
    equipment_text = " ".join([e.lower() for e in equipment])
    missing: Dict[str, List[str]] = {}
    for procedure in procedures:
        needed = required_equipment_for(procedure)
        if not needed:
            continue
        missing_items = [item for item in needed if item.lower() not in equipment_text]
        if missing_items:
            missing[procedure] = missing_items
    return missing


def contains_aspirational_language(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ASPIRATIONAL_KEYWORDS)


def contains_referral_language(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in REFERRAL_KEYWORDS)
