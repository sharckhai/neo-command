from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    session_id: str


class MapAction(BaseModel):
    type: str
    data: Optional[dict] = None


class FacilitySummary(BaseModel):
    pk_unique_id: str
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    facilityTypeId: Optional[str] = None
    normalized_region: Optional[str] = None
    address_city: Optional[str] = None
    confidence: Optional[float] = None


class ChatResponse(BaseModel):
    mode: str
    answer: str
    citations: List[str] = Field(default_factory=list)
    map_actions: List[MapAction] = Field(default_factory=list)
    facilities: List[FacilitySummary] = Field(default_factory=list)
