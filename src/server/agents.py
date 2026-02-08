from __future__ import annotations

from typing import List, Optional

import pandas as pd
from openai import OpenAI

from models.enums import GHANA_OFFICIAL_REGIONS
from server.config import settings
from server.models import ChatResponse, FacilitySummary, MapAction
from server.services.plan import build_plan_summary
from server.services.search import (
    count_keyword_by_region,
    facility_count_by_region,
    filter_facilities,
    filter_facilities_by_keyword,
    rare_procedures,
)
from server.services.verify import detect_equipment_gaps


VERIFY_KEYWORDS = ["suspicious", "verify", "trust", "claim", "mismatch", "real", "credible", "lack", "missing"]
PLAN_KEYWORDS = ["deploy", "send", "mission", "where should", "recommend", "prioritize", "plan"]
FACILITY_TYPES = ["hospital", "clinic", "pharmacy", "dentist", "doctor"]


def classify_mode(message: str) -> str:
    text = message.lower()
    if any(keyword in text for keyword in PLAN_KEYWORDS):
        return "plan"
    if any(keyword in text for keyword in VERIFY_KEYWORDS):
        return "verify"
    return "explore"


def extract_region(message: str) -> Optional[str]:
    text = message.lower()
    for region in GHANA_OFFICIAL_REGIONS:
        if region.lower() in text:
            return region
    return None


def build_map_actions(region: Optional[str]) -> List[MapAction]:
    if not region:
        return []
    return [MapAction(type="zoom_region", data={"region": region})]


def detect_facility_type(message: str) -> Optional[str]:
    text = message.lower()
    for facility_type in FACILITY_TYPES:
        if facility_type in text:
            return facility_type
    return None


def extract_keyword(message: str) -> Optional[str]:
    text = message.lower()
    for marker in ["have", "perform", "do", "treat", "treating", "with", "for"]:
        if marker in text:
            term = text.split(marker, 1)[1]
            for cutoff in [" in ", " within ", " near ", " around ", " across "]:
                if cutoff in term:
                    term = term.split(cutoff, 1)[0]
            term = term.strip(" ?.")
            if len(term) > 2:
                return term
    return None


def _build_facility_summaries(df: pd.DataFrame) -> List[FacilitySummary]:
    summaries = []
    for row in df.to_dict("records"):
        summaries.append(FacilitySummary(**row))
    return summaries


def _fallback_answer(mode: str) -> str:
    if mode == "verify":
        return (
            "I can check claims against listed equipment and flag facilities that appear "
            "overstated or missing prerequisites."
        )
    if mode == "plan":
        return (
            "I can compare regions on coverage, readiness, and equity to recommend a deployment option."
        )
    return "I can search facilities and summarize availability by region or service."


def generate_answer(message: str, mode: str) -> str:
    if not settings.openai_api_key:
        return _fallback_answer(mode)

    client = OpenAI(api_key=settings.openai_api_key)
    system_prompt = (
        "You are VirtueCommand, a healthcare intelligence assistant for NGO mission planners. "
        "Be concise, avoid speculation, and clearly state uncertainty."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or _fallback_answer(mode)


def _explore_response(message: str) -> ChatResponse:
    region = extract_region(message)
    facility_type = detect_facility_type(message)
    map_actions = build_map_actions(region)
    keyword = extract_keyword(message)

    if keyword and settings.entities_path.exists():
        matches_df = filter_facilities_by_keyword(keyword, region=region, limit=200)
        if facility_type and not matches_df.empty:
            matches_df = matches_df[
                matches_df["facilityTypeId"].str.lower() == facility_type.lower()
            ]
        count = len(matches_df.index)
        facilities = _build_facility_summaries(matches_df)
        answer = (
            f"I found {count} {facility_type or 'facilities'}"
            f"{(' in ' + region) if region else ''} mentioning {keyword}."
        )
        return ChatResponse(
            mode="explore",
            answer=answer,
            citations=[],
            map_actions=map_actions,
            facilities=facilities,
        )

    if "cold spot" in message.lower() or "desert" in message.lower():
        if keyword and settings.entities_path.exists():
            region_counts = count_keyword_by_region(keyword)
            ranked = sorted(region_counts.items(), key=lambda item: item[1])[:3]
            answer = (
                "Largest cold spots for "
                + keyword
                + ": "
                + ", ".join([f"{region} ({count})" for region, count in ranked])
                + "."
            )
            return ChatResponse(
                mode="explore",
                answer=answer,
                citations=[],
                map_actions=map_actions,
                facilities=[],
            )

    if "very few facilities" in message.lower() or "dependent on" in message.lower():
        if settings.entities_path.exists():
            rare = rare_procedures()
            if rare:
                answer = (
                    "Procedures with the fewest facilities: "
                    + ", ".join([f"{name} ({count})" for name, count in rare])
                    + "."
                )
            else:
                answer = "No procedure coverage data available."
            return ChatResponse(
                mode="explore",
                answer=answer,
                citations=[],
                map_actions=map_actions,
                facilities=[],
            )

    if settings.entities_path.exists():
        facilities_df = filter_facilities(region=region, facility_type=facility_type, limit=200)
        count = len(facilities_df.index)
        facilities = _build_facility_summaries(facilities_df)
        answer = (
            f"I found {count} {facility_type or 'facilities'}"
            f"{(' in ' + region) if region else ''}."
        )
        return ChatResponse(
            mode="explore",
            answer=answer,
            citations=[],
            map_actions=map_actions,
            facilities=facilities,
        )

    answer = generate_answer(message, "explore")
    return ChatResponse(
        mode="explore",
        answer=answer,
        citations=[],
        map_actions=map_actions,
        facilities=[],
    )


def _verify_response(message: str) -> ChatResponse:
    region = extract_region(message)
    map_actions = build_map_actions(region)
    if settings.entities_path.exists():
        df = pd.read_parquet(settings.entities_path)
        if region:
            df = df[df["normalized_region"] == region]
        flagged = []
        for row in df.to_dict("records"):
            missing = detect_equipment_gaps(
                procedures=row.get("procedure") or [],
                equipment=row.get("equipment") or [],
            )
            if missing:
                row_copy = dict(row)
                row_copy["missing_equipment"] = missing
                flagged.append(row_copy)
        flagged = flagged[:10]
        facility_rows = [
            {
                "pk_unique_id": row.get("pk_unique_id"),
                "name": row.get("name"),
                "lat": row.get("lat"),
                "lng": row.get("lng"),
                "facilityTypeId": row.get("facilityTypeId"),
                "normalized_region": row.get("normalized_region"),
                "address_city": row.get("address_city"),
                "confidence": row.get("confidence"),
            }
            for row in flagged
        ]
        facilities = [FacilitySummary(**row) for row in facility_rows if row.get("pk_unique_id")]
        if flagged:
            names = ", ".join([row.get("name", "Unknown") for row in flagged[:5]])
            answer = (
                "Flagged facilities with potential equipment gaps: " + names +
                ". Review each for missing prerequisites."
            )
        else:
            answer = "No obvious equipment gaps detected in the current slice."
        return ChatResponse(
            mode="verify",
            answer=answer,
            citations=[],
            map_actions=map_actions,
            facilities=facilities,
        )

    answer = generate_answer(message, "verify")
    return ChatResponse(
        mode="verify",
        answer=answer,
        citations=[],
        map_actions=map_actions,
        facilities=[],
    )


def _plan_response(message: str) -> ChatResponse:
    map_actions: List[MapAction] = []
    if settings.entities_path.exists():
        counts = facility_count_by_region()
        answer = build_plan_summary(counts)
        if counts:
            top_region = sorted(counts.items(), key=lambda item: item[1])[0][0]
            map_actions = build_map_actions(top_region)
        return ChatResponse(
            mode="plan",
            answer=answer,
            citations=[],
            map_actions=map_actions,
            facilities=[],
        )

    answer = generate_answer(message, "plan")
    return ChatResponse(
        mode="plan",
        answer=answer,
        citations=[],
        map_actions=[],
        facilities=[],
    )


def build_chat_response(message: str) -> ChatResponse:
    mode = classify_mode(message)
    if mode == "verify":
        return _verify_response(message)
    if mode == "plan":
        return _plan_response(message)
    return _explore_response(message)
