from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


def _load_external_module(path: Path, module_name: str):
    if not path.exists():
        raise FileNotFoundError(f"Missing external model file: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EXTERNAL_DIR = Path(__file__).resolve().parents[2] / "models" / "examples"
if not _EXTERNAL_DIR.exists():
    _EXTERNAL_DIR = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "prompts_and_pydantic_models"
        / "prompts_and_pydantic_models"
    )

_facility_mod = _load_external_module(_EXTERNAL_DIR / "facility_and_ngo_fields.py", "facility_and_ngo_fields")
_free_form_mod = _load_external_module(_EXTERNAL_DIR / "free_form.py", "free_form")

BaseOrganization = _facility_mod.BaseOrganization
Facility = _facility_mod.Facility
NGO = _facility_mod.NGO
FacilityFacts = _free_form_mod.FacilityFacts


class VerifiedCapability(BaseModel):
    statement: str = Field(..., description="Capability statement that appears supported by evidence")
    confidence: float = Field(..., description="Confidence score between 0 and 1")


class FacilityFingerprint(BaseModel):
    capability_summary: Optional[str] = Field(
        None, description="Short summary of the facility's capabilities"
    )
    verified_capabilities: Optional[List[VerifiedCapability]] = Field(
        None, description="Capability claims with confidence values"
    )
    anomaly_flags: Optional[List[str]] = Field(None, description="Anomaly or risk flags")
    upgrade_potential: Optional[str] = Field(
        None, description="Suggested upgrade or growth potential"
    )
    service_permanence: Optional[str] = Field(
        None, description="Whether services are permanent or visiting"
    )


class CleanedEntity(Facility):
    lat: Optional[float] = None
    lng: Optional[float] = None
    geocode_confidence: Optional[str] = None
    normalized_region: Optional[str] = None
    source_urls: Optional[List[str]] = None
    source_types: Optional[List[str]] = None
    source_count: Optional[int] = None
    confidence: Optional[float] = None
    quality_flags: Optional[List[str]] = None
    fingerprint: Optional[dict] = None

    countries: Optional[List[str]] = None
    missionStatement: Optional[str] = None
    missionStatementLink: Optional[str] = None
    organizationDescription: Optional[str] = None
