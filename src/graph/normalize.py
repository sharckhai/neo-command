"""Free-text → canonical node IDs via keyword matching + LLM batch fallback."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Canonical vocabularies — each entry has a canonical key, display name,
# category, and a list of lowercase aliases for regex matching.
# ---------------------------------------------------------------------------

CANONICAL_EQUIPMENT: dict[str, dict] = {
    # Surgical
    "operating_theatre": {
        "display": "Operating Theatre",
        "category": "surgical",
        "aliases": [
            "operating room", "operating theatre", "operating theater",
            "surgical theatre", "surgical theater", "surgical room", "theatre",
            "or suite", "surgical suite",
        ],
    },
    "operating_microscope": {
        "display": "Operating Microscope",
        "category": "surgical",
        "aliases": ["operating microscope", "surgical microscope", "microsurgery microscope"],
    },
    "autoclave": {
        "display": "Autoclave / Sterilizer",
        "category": "surgical",
        "aliases": ["autoclave", "sterilizer", "sterilization", "sterilisation", "steam sterilizer"],
    },
    "anesthesia_machine": {
        "display": "Anesthesia Machine",
        "category": "surgical",
        "aliases": [
            "anesthesia machine", "anaesthesia machine", "anesthesia equipment",
            "anaesthesia equipment", "anesthetic machine",
        ],
    },
    "ventilator": {
        "display": "Ventilator",
        "category": "surgical",
        "aliases": ["ventilator", "mechanical ventilator", "breathing machine", "respirator"],
    },
    "patient_monitor": {
        "display": "Patient Monitor",
        "category": "monitoring",
        "aliases": [
            "patient monitor", "vital signs monitor", "cardiac monitor",
            "bedside monitor", "multiparameter monitor",
        ],
    },
    "defibrillator": {
        "display": "Defibrillator",
        "category": "surgical",
        "aliases": ["defibrillator", "aed", "automated external defibrillator"],
    },
    "suction_machine": {
        "display": "Suction Machine",
        "category": "surgical",
        "aliases": ["suction machine", "suction apparatus", "suction pump", "surgical suction"],
    },
    "electrosurgical_unit": {
        "display": "Electrosurgical Unit",
        "category": "surgical",
        "aliases": [
            "electrosurgical unit", "diathermy", "cautery", "electrocautery",
            "bovie", "surgical cautery",
        ],
    },
    # Imaging
    "xray_machine": {
        "display": "X-ray Machine",
        "category": "imaging",
        "aliases": ["x-ray", "xray", "x ray", "radiograph", "radiography"],
    },
    "ct_scanner": {
        "display": "CT Scanner",
        "category": "imaging",
        "aliases": [
            "ct scanner", "ct scan", "cat scan", "computed tomography",
            "ct machine", "ct imaging",
        ],
    },
    "mri_scanner": {
        "display": "MRI Scanner",
        "category": "imaging",
        "aliases": [
            "mri", "mri scanner", "mri machine", "magnetic resonance",
            "magnetic resonance imaging",
        ],
    },
    "ultrasound": {
        "display": "Ultrasound Machine",
        "category": "imaging",
        "aliases": [
            "ultrasound", "ultrasonography", "sonography", "sonogram",
            "ultrasound machine", "ultrasound device", "echo", "echocardiography",
            "doppler ultrasound",
        ],
    },
    "mammography": {
        "display": "Mammography Machine",
        "category": "imaging",
        "aliases": ["mammography", "mammogram", "mammography machine"],
    },
    "fluoroscopy": {
        "display": "Fluoroscopy",
        "category": "imaging",
        "aliases": ["fluoroscopy", "fluoroscope", "c-arm", "image intensifier"],
    },
    "oct_machine": {
        "display": "OCT Machine",
        "category": "imaging",
        "aliases": [
            "oct", "optical coherence tomography", "oct machine",
            "oct imaging", "macular oct",
        ],
    },
    "fundus_camera": {
        "display": "Fundus Camera",
        "category": "imaging",
        "aliases": [
            "fundus camera", "fundus photography", "retinal camera",
            "fundus fluorescein angiography", "ffa",
        ],
    },
    "slit_lamp": {
        "display": "Slit Lamp",
        "category": "imaging",
        "aliases": ["slit lamp", "slit-lamp", "biomicroscope"],
    },
    "visual_field_tester": {
        "display": "Visual Field Tester",
        "category": "imaging",
        "aliases": [
            "visual field", "perimetry", "perimeter", "visual field testing",
            "humphrey", "goldmann",
        ],
    },
    "b_scan_ultrasound": {
        "display": "B-Scan Ultrasound",
        "category": "imaging",
        "aliases": ["b-scan", "b scan", "ocular ultrasonography", "b-scan ultrasound"],
    },
    "keratometer": {
        "display": "Keratometer",
        "category": "imaging",
        "aliases": ["keratometer", "keratoscopy", "keratoscope"],
    },
    "a_scan_biometry": {
        "display": "A-Scan Biometry",
        "category": "imaging",
        "aliases": ["a-scan", "a scan", "biometry", "iol master", "a-scan biometry"],
    },
    "dental_xray": {
        "display": "Dental X-ray",
        "category": "imaging",
        "aliases": [
            "dental x-ray", "dental xray", "dental radiograph",
            "panoramic x-ray", "orthopantomogram", "opg",
        ],
    },
    "ecg_machine": {
        "display": "ECG Machine",
        "category": "monitoring",
        "aliases": [
            "ecg", "ekg", "electrocardiogram", "electrocardiograph",
            "ecg machine", "ekg machine",
        ],
    },
    # Lab
    "laboratory": {
        "display": "Laboratory",
        "category": "lab",
        "aliases": [
            "laboratory", "medical lab", "clinical lab", "lab facilities",
            "pathology lab", "diagnostic lab",
        ],
    },
    "blood_bank": {
        "display": "Blood Bank",
        "category": "lab",
        "aliases": [
            "blood bank", "blood transfusion", "blood storage",
            "transfusion services", "blood supply",
        ],
    },
    "hematology_analyzer": {
        "display": "Hematology Analyzer",
        "category": "lab",
        "aliases": [
            "hematology analyzer", "haematology analyzer", "cbc machine",
            "blood cell counter", "hematology",
        ],
    },
    "chemistry_analyzer": {
        "display": "Chemistry Analyzer",
        "category": "lab",
        "aliases": [
            "chemistry analyzer", "biochemistry analyzer", "clinical chemistry",
            "blood chemistry", "metabolic panel",
        ],
    },
    "microscope": {
        "display": "Microscope",
        "category": "lab",
        "aliases": ["microscope", "light microscope", "lab microscope"],
    },
    # Infrastructure
    "oxygen_supply": {
        "display": "Oxygen Supply",
        "category": "infrastructure",
        "aliases": [
            "oxygen", "oxygen supply", "piped oxygen", "oxygen plant",
            "oxygen concentrator", "oxygen generation", "o2",
        ],
    },
    "pharmacy": {
        "display": "Pharmacy / Dispensary",
        "category": "infrastructure",
        "aliases": ["pharmacy", "dispensary", "drug dispensary", "on-site pharmacy"],
    },
    "ambulance": {
        "display": "Ambulance",
        "category": "infrastructure",
        "aliases": ["ambulance", "emergency vehicle", "ambulance service"],
    },
    "generator": {
        "display": "Backup Generator",
        "category": "infrastructure",
        "aliases": [
            "generator", "backup generator", "backup power", "standby generator",
            "power backup", "diesel generator",
        ],
    },
    "incubator": {
        "display": "Incubator",
        "category": "infrastructure",
        "aliases": ["incubator", "neonatal incubator", "baby incubator", "infant incubator"],
    },
    "dialysis_machine": {
        "display": "Dialysis Machine",
        "category": "therapeutic",
        "aliases": [
            "dialysis", "hemodialysis", "haemodialysis", "dialysis machine",
            "dialysis center", "dialysis unit", "renal dialysis",
        ],
    },
    "phacoemulsification_machine": {
        "display": "Phacoemulsification Machine",
        "category": "surgical",
        "aliases": [
            "phacoemulsification", "phaco", "phaco machine",
            "cataract phaco", "phacoemulsifier",
        ],
    },
    "laser_machine": {
        "display": "Laser Machine",
        "category": "surgical",
        "aliases": [
            "laser", "laser machine", "laser surgery", "laser equipment",
            "yag laser", "argon laser", "excimer laser", "laser eye",
        ],
    },
    "endoscope": {
        "display": "Endoscope",
        "category": "surgical",
        "aliases": [
            "endoscope", "endoscopy", "gastroscope", "colonoscope",
            "bronchoscope", "laparoscope", "laparoscopy", "arthroscope",
        ],
    },
    "dental_chair": {
        "display": "Dental Chair / Unit",
        "category": "surgical",
        "aliases": [
            "dental chair", "dental unit", "dental equipment",
            "dental facilities", "dental suite",
        ],
    },
    "physiotherapy_equipment": {
        "display": "Physiotherapy Equipment",
        "category": "therapeutic",
        "aliases": [
            "physiotherapy", "physical therapy", "rehabilitation equipment",
            "physio equipment", "rehab equipment",
        ],
    },
    "radiation_therapy": {
        "display": "Radiation Therapy Equipment",
        "category": "therapeutic",
        "aliases": [
            "radiation therapy", "radiotherapy", "linear accelerator",
            "linac", "cobalt 60", "brachytherapy",
        ],
    },
    "nuclear_medicine": {
        "display": "Nuclear Medicine Equipment",
        "category": "imaging",
        "aliases": [
            "nuclear medicine", "gamma camera", "spect", "pet scan",
            "pet-ct", "nuclear imaging",
        ],
    },
    "eeg_machine": {
        "display": "EEG Machine",
        "category": "monitoring",
        "aliases": ["eeg", "electroencephalogram", "electroencephalography", "eeg machine"],
    },
    "emg_machine": {
        "display": "EMG Machine",
        "category": "monitoring",
        "aliases": ["emg", "electromyography", "electromyogram", "nerve conduction"],
    },
    "pulse_oximeter": {
        "display": "Pulse Oximeter",
        "category": "monitoring",
        "aliases": ["pulse oximeter", "oximeter", "spo2", "oxygen saturation monitor"],
    },
    "infusion_pump": {
        "display": "Infusion Pump",
        "category": "therapeutic",
        "aliases": ["infusion pump", "iv pump", "syringe pump", "syringe driver"],
    },
    "robotic_surgery": {
        "display": "Robotic Surgical System",
        "category": "surgical",
        "aliases": [
            "robotic surgery", "da vinci", "surgical robot",
            "robotic surgical system",
        ],
    },
    "cath_lab": {
        "display": "Catheterization Lab",
        "category": "surgical",
        "aliases": [
            "cath lab", "catheterization lab", "cardiac catheterization",
            "cardiac cath", "angiography suite",
        ],
    },
}

CANONICAL_CAPABILITIES: dict[str, dict] = {
    # Surgical
    "cataract_surgery": {
        "display": "Cataract Surgery",
        "category": "surgical",
        "complexity": "medium",
        "aliases": [
            "cataract surgery", "cataract", "cataract removal",
            "phacoemulsification", "lens implant", "iol implant",
            "cataract extraction",
        ],
    },
    "general_surgery": {
        "display": "General Surgery",
        "category": "surgical",
        "complexity": "high",
        "aliases": [
            "general surgery", "surgical services", "major surgery",
            "minor surgery", "major and minor surgeries", "surgical operations",
        ],
    },
    "cesarean_section": {
        "display": "Cesarean Section",
        "category": "maternity",
        "complexity": "high",
        "aliases": [
            "cesarean", "caesarean", "c-section", "cesarean section",
            "caesarean section", "c section", "emergency cesarean",
        ],
    },
    "orthopedic_surgery": {
        "display": "Orthopedic Surgery",
        "category": "surgical",
        "complexity": "high",
        "aliases": [
            "orthopedic surgery", "orthopaedic surgery", "orthopedic",
            "fracture repair", "joint replacement", "bone surgery",
        ],
    },
    "eye_surgery": {
        "display": "Eye Surgery",
        "category": "surgical",
        "complexity": "high",
        "aliases": [
            "eye surgery", "ophthalmic surgery", "ocular surgery",
            "vitrectomy", "glaucoma surgery", "retinal surgery",
            "cornea transplant", "enucleation",
        ],
    },
    "dental_services": {
        "display": "Dental Services",
        "category": "surgical",
        "complexity": "low",
        "aliases": [
            "dental services", "dental care", "dental treatment",
            "dentistry", "dental clinic", "dental extraction",
            "root canal", "filling", "dental filling",
        ],
    },
    "laparoscopic_surgery": {
        "display": "Laparoscopic Surgery",
        "category": "surgical",
        "complexity": "high",
        "aliases": [
            "laparoscopic", "laparoscopy", "minimally invasive surgery",
            "keyhole surgery",
        ],
    },
    "endoscopy": {
        "display": "Endoscopy",
        "category": "diagnostic",
        "complexity": "medium",
        "aliases": [
            "endoscopy", "gastroscopy", "colonoscopy", "upper gi endoscopy",
            "lower gi endoscopy", "bronchoscopy",
        ],
    },
    "cardiac_surgery": {
        "display": "Cardiac Surgery",
        "category": "surgical",
        "complexity": "high",
        "aliases": [
            "cardiac surgery", "heart surgery", "open heart surgery",
            "bypass surgery", "cabg", "valve surgery", "valve replacement",
        ],
    },
    "neurosurgery": {
        "display": "Neurosurgery",
        "category": "surgical",
        "complexity": "high",
        "aliases": [
            "neurosurgery", "brain surgery", "craniotomy", "spinal surgery",
            "spine surgery",
        ],
    },
    "plastic_surgery": {
        "display": "Plastic Surgery",
        "category": "surgical",
        "complexity": "high",
        "aliases": [
            "plastic surgery", "reconstructive surgery", "cleft repair",
            "cleft lip", "cleft palate", "burn surgery", "skin graft",
        ],
    },
    "urology_surgery": {
        "display": "Urology Surgery",
        "category": "surgical",
        "complexity": "high",
        "aliases": [
            "urology surgery", "urological surgery", "prostatectomy",
            "lithotripsy", "cystoscopy", "kidney stone removal",
        ],
    },
    # Diagnostic
    "laboratory_services": {
        "display": "Laboratory Services",
        "category": "diagnostic",
        "complexity": "low",
        "aliases": [
            "laboratory services", "lab services", "lab testing",
            "laboratory testing", "blood test", "clinical laboratory",
            "diagnostic testing",
        ],
    },
    "xray_imaging": {
        "display": "X-ray Imaging",
        "category": "diagnostic",
        "complexity": "low",
        "aliases": [
            "x-ray imaging", "xray imaging", "x-ray services",
            "radiography", "x-ray",
        ],
    },
    "ultrasound_imaging": {
        "display": "Ultrasound Imaging",
        "category": "diagnostic",
        "complexity": "low",
        "aliases": [
            "ultrasound imaging", "ultrasound scan", "sonography",
            "ultrasound services", "obstetric ultrasound",
        ],
    },
    "ct_imaging": {
        "display": "CT Imaging",
        "category": "diagnostic",
        "complexity": "medium",
        "aliases": ["ct imaging", "ct scan", "ct services", "computed tomography"],
    },
    "mri_imaging": {
        "display": "MRI Imaging",
        "category": "diagnostic",
        "complexity": "medium",
        "aliases": ["mri imaging", "mri scan", "mri services", "magnetic resonance imaging"],
    },
    "ecg_services": {
        "display": "ECG Services",
        "category": "diagnostic",
        "complexity": "low",
        "aliases": [
            "ecg", "ekg", "electrocardiogram", "electrocardiography",
            "ecg services",
        ],
    },
    "eye_examination": {
        "display": "Eye Examination",
        "category": "diagnostic",
        "complexity": "low",
        "aliases": [
            "eye examination", "eye exam", "eye care", "vision test",
            "refraction", "ophthalmology consultation", "eye check",
            "eye care services",
        ],
    },
    # Emergency
    "emergency_services": {
        "display": "Emergency Services",
        "category": "emergency",
        "complexity": "high",
        "aliases": [
            "emergency services", "emergency care", "emergency department",
            "emergency room", "24-hour emergency", "24/7 emergency",
            "24hr emergency", "accident and emergency", "a&e",
            "casualty", "trauma care",
        ],
    },
    "icu_services": {
        "display": "ICU Services",
        "category": "emergency",
        "complexity": "high",
        "aliases": [
            "icu", "intensive care", "intensive care unit", "critical care",
            "high dependency unit", "hdu",
        ],
    },
    "nicu_services": {
        "display": "NICU Services",
        "category": "emergency",
        "complexity": "high",
        "aliases": [
            "nicu", "neonatal icu", "neonatal intensive care",
            "newborn intensive care", "special care baby unit", "scbu",
        ],
    },
    # Maternity
    "maternity_services": {
        "display": "Maternity Services",
        "category": "maternity",
        "complexity": "medium",
        "aliases": [
            "maternity", "maternity services", "antenatal care", "anc",
            "postnatal care", "obstetric care", "delivery services",
            "labour ward", "labor ward", "birthing",
        ],
    },
    "family_planning": {
        "display": "Family Planning",
        "category": "maternity",
        "complexity": "low",
        "aliases": [
            "family planning", "contraception", "reproductive health",
            "birth control", "pmtct",
        ],
    },
    # Therapeutic
    "dialysis": {
        "display": "Dialysis Services",
        "category": "therapeutic",
        "complexity": "high",
        "aliases": [
            "dialysis", "hemodialysis", "haemodialysis", "renal dialysis",
            "dialysis center", "dialysis unit",
        ],
    },
    "chemotherapy": {
        "display": "Chemotherapy",
        "category": "therapeutic",
        "complexity": "high",
        "aliases": [
            "chemotherapy", "chemo", "cancer treatment", "oncology treatment",
            "cancer therapy",
        ],
    },
    "radiotherapy": {
        "display": "Radiotherapy",
        "category": "therapeutic",
        "complexity": "high",
        "aliases": [
            "radiotherapy", "radiation therapy", "radiation treatment",
            "cobalt therapy",
        ],
    },
    "physiotherapy": {
        "display": "Physiotherapy",
        "category": "therapeutic",
        "complexity": "low",
        "aliases": [
            "physiotherapy", "physical therapy", "rehabilitation",
            "physio", "rehab", "occupational therapy",
        ],
    },
    "hiv_treatment": {
        "display": "HIV/AIDS Treatment",
        "category": "therapeutic",
        "complexity": "medium",
        "aliases": [
            "hiv", "aids", "hiv treatment", "hiv/aids", "antiretroviral",
            "art", "hiv testing", "hiv counseling", "hct",
        ],
    },
    "mental_health": {
        "display": "Mental Health Services",
        "category": "therapeutic",
        "complexity": "medium",
        "aliases": [
            "mental health", "psychiatric", "psychiatry", "psychology",
            "counseling", "counselling", "behavioral health",
        ],
    },
    "vaccination": {
        "display": "Vaccination / Immunization",
        "category": "general",
        "complexity": "low",
        "aliases": [
            "vaccination", "immunization", "immunisation", "vaccine",
            "travel immunisation", "travel vaccination",
        ],
    },
    # General
    "outpatient_services": {
        "display": "Outpatient Services (OPD)",
        "category": "general",
        "complexity": "low",
        "aliases": [
            "outpatient", "opd", "outpatient department", "outpatient services",
            "general consultation", "medical consultation", "general opd",
            "specialist consultation",
        ],
    },
    "inpatient_services": {
        "display": "Inpatient Services",
        "category": "general",
        "complexity": "medium",
        "aliases": [
            "inpatient", "in-patient", "admission", "ward",
            "inpatient care", "inpatient services", "hospitalization",
        ],
    },
    "pediatric_care": {
        "display": "Pediatric Care",
        "category": "general",
        "complexity": "medium",
        "aliases": [
            "pediatric", "paediatric", "pediatrics", "children's health",
            "child health", "pediatric care", "child care",
        ],
    },
    "pharmacy_services": {
        "display": "Pharmacy Services",
        "category": "general",
        "complexity": "low",
        "aliases": [
            "pharmacy", "dispensary", "pharmacy services", "medications",
            "drug dispensary",
        ],
    },
}


# ---------------------------------------------------------------------------
# Build reverse lookup (alias → canonical key) at import time
# ---------------------------------------------------------------------------

def _build_alias_index(canonical_dict: dict[str, dict]) -> list[tuple[re.Pattern, str]]:
    """Build a list of (compiled_regex, canonical_key) sorted longest-first."""
    pairs: list[tuple[str, str]] = []
    for key, meta in canonical_dict.items():
        for alias in meta["aliases"]:
            pairs.append((alias, key))
    # Sort by alias length descending so longer/more-specific matches win
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    # Compile as word-boundary regexes (s?/es? handles plurals)
    compiled = []
    for alias, key in pairs:
        # Add optional plural suffix: "theatre" matches "theatres", "ambulance" matches "ambulances"
        pattern = r"\b" + re.escape(alias) + r"(?:e?s)?\b"
        compiled.append((re.compile(pattern, re.IGNORECASE), key))
    return compiled


_EQUIPMENT_INDEX = _build_alias_index(CANONICAL_EQUIPMENT)
_CAPABILITY_INDEX = _build_alias_index(CANONICAL_CAPABILITIES)

# Version hash of canonical vocabularies — cache is invalidated when this changes
_VOCAB_VERSION = hashlib.md5(
    json.dumps(
        sorted(CANONICAL_EQUIPMENT.keys()) + sorted(CANONICAL_CAPABILITIES.keys())
    ).encode()
).hexdigest()[:8]

_NO_MATCH = "__no_match__"


# ---------------------------------------------------------------------------
# Pass 1: keyword/regex matching
# ---------------------------------------------------------------------------

def match_equipment(text: str) -> list[tuple[str, float]]:
    """Return list of (canonical_key, confidence) for equipment found in text."""
    if not text or not text.strip():
        return []
    found: dict[str, float] = {}
    for pattern, key in _EQUIPMENT_INDEX:
        if pattern.search(text) and key not in found:
            found[key] = 0.8  # keyword match confidence
    return list(found.items())


def match_capabilities(text: str) -> list[tuple[str, float]]:
    """Return list of (canonical_key, confidence) for capabilities found in text."""
    if not text or not text.strip():
        return []
    found: dict[str, float] = {}
    for pattern, key in _CAPABILITY_INDEX:
        if pattern.search(text) and key not in found:
            found[key] = 0.8
    return list(found.items())


# ---------------------------------------------------------------------------
# Pass 2: LLM batch classification (cached)
# ---------------------------------------------------------------------------

_CACHE_PATH = Path(__file__).parent.parent.parent / "data" / "normalization_cache.json"


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH) as f:
            data = json.load(f)
        if data.get("_version") == _VOCAB_VERSION:
            return data
        # Vocabulary changed — discard stale cache
    return {"_version": _VOCAB_VERSION, "equipment": {}, "capabilities": {}}


def _save_cache(cache: dict) -> None:
    cache["_version"] = _VOCAB_VERSION
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def _llm_classify_batch(
    items: list[str],
    domain: str,
    canonical_keys: list[str],
) -> dict[str, Optional[str]]:
    """Classify unmatched items using OpenAI GPT-4o-mini.

    Returns mapping of raw_text → canonical_key (or None if no match).
    """
    # Check if OpenAI is available
    try:
        from openai import OpenAI
    except ImportError:
        return {item: None for item in items}

    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {item: None for item in items}

    client = OpenAI(api_key=api_key)
    results: dict[str, Optional[str]] = {}

    # Process in batches of 20
    for i in range(0, len(items), 20):
        batch = items[i : i + 20]
        prompt = (
            f"You are classifying medical {domain} terms.\n"
            f"For each item below, map it to the BEST matching canonical key from this list, "
            f"or respond 'NONE' if no good match exists.\n\n"
            f"Canonical keys:\n{json.dumps(canonical_keys, indent=2)}\n\n"
            f"Items to classify:\n"
        )
        for j, item in enumerate(batch):
            prompt += f"{j + 1}. {item}\n"

        prompt += (
            "\nRespond with a JSON object mapping each item (exact text) to its canonical key or null. "
            "Example: {\"item text\": \"canonical_key\", \"other item\": null}"
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            for item in batch:
                val = parsed.get(item)
                if val and val != "NONE" and val in canonical_keys:
                    results[item] = val
                else:
                    results[item] = None
        except Exception:
            for item in batch:
                results[item] = None

    return results


def normalize_equipment_list(raw_items: list[str]) -> list[tuple[str, float, str]]:
    """Normalize a list of raw equipment strings.

    Returns list of (canonical_key, confidence, raw_text).
    Uses keyword matching first, then LLM for unmatched items.
    """
    results: list[tuple[str, float, str]] = []
    unmatched: list[str] = []
    cache = _load_cache()

    for raw in raw_items:
        raw = raw.strip()
        if not raw:
            continue

        # Try keyword match
        matches = match_equipment(raw)
        if matches:
            for key, conf in matches:
                results.append((key, conf, raw))
            continue

        cached = cache.get("equipment", {}).get(raw.lower())
        if cached == _NO_MATCH:
            continue  # known miss — skip LLM
        elif cached:
            results.append((cached, 0.6, raw))
        else:
            unmatched.append(raw)

    # LLM pass for unmatched
    if unmatched:
        canonical_keys = list(CANONICAL_EQUIPMENT.keys())
        llm_results = _llm_classify_batch(unmatched, "equipment", canonical_keys)

        eq_cache = cache.setdefault("equipment", {})
        for raw_text, canonical in llm_results.items():
            if canonical:
                eq_cache[raw_text.lower()] = canonical
                results.append((canonical, 0.6, raw_text))
            else:
                eq_cache[raw_text.lower()] = _NO_MATCH
        _save_cache(cache)

    return results


def normalize_capability_list(raw_items: list[str], source_field: str = "capability") -> list[tuple[str, float, str, str]]:
    """Normalize a list of raw capability/procedure strings.

    Returns list of (canonical_key, confidence, raw_text, source_field).
    """
    results: list[tuple[str, float, str, str]] = []
    unmatched: list[str] = []
    cache = _load_cache()

    for raw in raw_items:
        raw = raw.strip()
        if not raw:
            continue

        # Try keyword match
        matches = match_capabilities(raw)
        if matches:
            for key, conf in matches:
                results.append((key, conf, raw, source_field))
            continue

        cached = cache.get("capabilities", {}).get(raw.lower())
        if cached == _NO_MATCH:
            continue  # known miss — skip LLM
        elif cached:
            results.append((cached, 0.6, raw, source_field))
        else:
            unmatched.append(raw)

    # LLM pass for unmatched
    if unmatched:
        canonical_keys = list(CANONICAL_CAPABILITIES.keys())
        llm_results = _llm_classify_batch(unmatched, "capabilities", canonical_keys)

        cap_cache = cache.setdefault("capabilities", {})
        for raw_text, canonical in llm_results.items():
            if canonical:
                cap_cache[raw_text.lower()] = canonical
                results.append((canonical, 0.6, raw_text, source_field))
            else:
                cap_cache[raw_text.lower()] = _NO_MATCH
        _save_cache(cache)

    return results
