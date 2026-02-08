"""Static mapping of capabilities → required and recommended equipment.

Used by inference.py to compute LACKS and COULD_SUPPORT edges.
No LLM at runtime — these are deterministic, auditable, version-controlled.
"""

# Each capability maps to:
#   required:    equipment that MUST be present for the capability to be credible
#   recommended: equipment that is typical but not strictly necessary

CAPABILITY_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    # --- Surgical ---
    "cataract_surgery": {
        "required": [
            "operating_theatre",
            "operating_microscope",
            "autoclave",
            "anesthesia_machine",
        ],
        "recommended": [
            "phacoemulsification_machine",
            "a_scan_biometry",
            "slit_lamp",
            "keratometer",
        ],
    },
    "general_surgery": {
        "required": [
            "operating_theatre",
            "autoclave",
            "anesthesia_machine",
            "patient_monitor",
        ],
        "recommended": [
            "electrosurgical_unit",
            "suction_machine",
            "ventilator",
            "blood_bank",
            "oxygen_supply",
        ],
    },
    "cesarean_section": {
        "required": [
            "operating_theatre",
            "anesthesia_machine",
            "autoclave",
            "blood_bank",
            "patient_monitor",
        ],
        "recommended": [
            "ventilator",
            "oxygen_supply",
            "incubator",
            "suction_machine",
        ],
    },
    "orthopedic_surgery": {
        "required": [
            "operating_theatre",
            "anesthesia_machine",
            "autoclave",
            "xray_machine",
        ],
        "recommended": [
            "fluoroscopy",
            "patient_monitor",
            "electrosurgical_unit",
            "blood_bank",
        ],
    },
    "eye_surgery": {
        "required": [
            "operating_theatre",
            "operating_microscope",
            "autoclave",
            "anesthesia_machine",
        ],
        "recommended": [
            "slit_lamp",
            "oct_machine",
            "visual_field_tester",
            "laser_machine",
        ],
    },
    "dental_services": {
        "required": [
            "dental_chair",
        ],
        "recommended": [
            "dental_xray",
            "autoclave",
        ],
    },
    "laparoscopic_surgery": {
        "required": [
            "operating_theatre",
            "endoscope",
            "anesthesia_machine",
            "autoclave",
            "patient_monitor",
        ],
        "recommended": [
            "electrosurgical_unit",
            "suction_machine",
            "ventilator",
        ],
    },
    "cardiac_surgery": {
        "required": [
            "operating_theatre",
            "anesthesia_machine",
            "ventilator",
            "patient_monitor",
            "blood_bank",
            "defibrillator",
        ],
        "recommended": [
            "cath_lab",
            "ecg_machine",
            "oxygen_supply",
            "ultrasound",
        ],
    },
    "neurosurgery": {
        "required": [
            "operating_theatre",
            "operating_microscope",
            "anesthesia_machine",
            "ventilator",
            "patient_monitor",
            "ct_scanner",
        ],
        "recommended": [
            "mri_scanner",
            "electrosurgical_unit",
            "blood_bank",
        ],
    },
    "plastic_surgery": {
        "required": [
            "operating_theatre",
            "anesthesia_machine",
            "autoclave",
            "operating_microscope",
        ],
        "recommended": [
            "electrosurgical_unit",
            "suction_machine",
        ],
    },
    "urology_surgery": {
        "required": [
            "operating_theatre",
            "anesthesia_machine",
            "autoclave",
            "endoscope",
        ],
        "recommended": [
            "ultrasound",
            "xray_machine",
            "fluoroscopy",
        ],
    },
    # --- Diagnostic ---
    "endoscopy": {
        "required": [
            "endoscope",
            "patient_monitor",
        ],
        "recommended": [
            "suction_machine",
            "anesthesia_machine",
            "autoclave",
        ],
    },
    "laboratory_services": {
        "required": [
            "laboratory",
        ],
        "recommended": [
            "microscope",
            "hematology_analyzer",
            "chemistry_analyzer",
        ],
    },
    "xray_imaging": {
        "required": [
            "xray_machine",
        ],
        "recommended": [],
    },
    "ultrasound_imaging": {
        "required": [
            "ultrasound",
        ],
        "recommended": [],
    },
    "ct_imaging": {
        "required": [
            "ct_scanner",
        ],
        "recommended": [],
    },
    "mri_imaging": {
        "required": [
            "mri_scanner",
        ],
        "recommended": [],
    },
    "ecg_services": {
        "required": [
            "ecg_machine",
        ],
        "recommended": [],
    },
    "eye_examination": {
        "required": [
            "slit_lamp",
        ],
        "recommended": [
            "visual_field_tester",
            "oct_machine",
            "fundus_camera",
            "keratometer",
        ],
    },
    # --- Emergency ---
    "emergency_services": {
        "required": [
            "defibrillator",
            "patient_monitor",
            "oxygen_supply",
        ],
        "recommended": [
            "ventilator",
            "suction_machine",
            "xray_machine",
            "ambulance",
        ],
    },
    "icu_services": {
        "required": [
            "ventilator",
            "patient_monitor",
            "oxygen_supply",
            "infusion_pump",
        ],
        "recommended": [
            "defibrillator",
            "suction_machine",
            "ecg_machine",
        ],
    },
    "nicu_services": {
        "required": [
            "incubator",
            "patient_monitor",
            "oxygen_supply",
        ],
        "recommended": [
            "ventilator",
            "infusion_pump",
            "pulse_oximeter",
        ],
    },
    # --- Maternity ---
    "maternity_services": {
        "required": [
            "ultrasound",
        ],
        "recommended": [
            "patient_monitor",
            "incubator",
            "oxygen_supply",
        ],
    },
    "family_planning": {
        "required": [],
        "recommended": [
            "ultrasound",
        ],
    },
    # --- Therapeutic ---
    "dialysis": {
        "required": [
            "dialysis_machine",
            "patient_monitor",
        ],
        "recommended": [
            "laboratory",
            "oxygen_supply",
        ],
    },
    "chemotherapy": {
        "required": [
            "infusion_pump",
            "patient_monitor",
            "laboratory",
        ],
        "recommended": [
            "pharmacy",
        ],
    },
    "radiotherapy": {
        "required": [
            "radiation_therapy",
        ],
        "recommended": [
            "ct_scanner",
            "patient_monitor",
        ],
    },
    "physiotherapy": {
        "required": [
            "physiotherapy_equipment",
        ],
        "recommended": [],
    },
    "hiv_treatment": {
        "required": [
            "laboratory",
        ],
        "recommended": [
            "pharmacy",
        ],
    },
    "mental_health": {
        "required": [],
        "recommended": [
            "pharmacy",
        ],
    },
    # --- General ---
    "vaccination": {
        "required": [],
        "recommended": [
            "pharmacy",
        ],
    },
    "outpatient_services": {
        "required": [],
        "recommended": [
            "pharmacy",
            "laboratory",
        ],
    },
    "inpatient_services": {
        "required": [
            "patient_monitor",
        ],
        "recommended": [
            "pharmacy",
            "laboratory",
            "oxygen_supply",
        ],
    },
    "pediatric_care": {
        "required": [],
        "recommended": [
            "patient_monitor",
            "incubator",
            "pharmacy",
        ],
    },
    "pharmacy_services": {
        "required": [
            "pharmacy",
        ],
        "recommended": [],
    },
}
