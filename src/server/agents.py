from __future__ import annotations

from typing import List, Optional

import pandas as pd
from openai import OpenAI

from models.enums import GHANA_OFFICIAL_REGIONS
from server.config import settings
from server.data.warehouse import DuckDbWarehouse
from server.models import ChatResponse, FacilitySummary, MapAction
from server.tools import flag_facilities_with_missing_equipment


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

    if settings.entities_path.exists():
        warehouse = DuckDbWarehouse()
        where_clauses = []
        if region:
            where_clauses.append(f"normalized_region = '{region}'")
        if facility_type:
            where_clauses.append(f"lower(facilityTypeId) = '{facility_type}'")
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        count_sql = f"SELECT COUNT(*) FROM facilities{where_sql}"
        count = warehouse.query(count_sql)[0][0]
        summary_sql = (
            "SELECT pk_unique_id, name, lat, lng, facilityTypeId, normalized_region, "
            "address_city, confidence FROM facilities "
        ) + where_sql + " LIMIT 200"
        facilities_df = warehouse.query_df(summary_sql)
        facilities = _build_facility_summaries(facilities_df)
        answer = f\"I found {count} {facility_type or 'facilities'}{(' in ' + region) if region else ''}.\"\n        return ChatResponse(\n            mode=\"explore\",\n            answer=answer,\n            citations=[],\n            map_actions=map_actions,\n            facilities=facilities,\n        )\n\n    answer = generate_answer(message, \"explore\")\n    return ChatResponse(\n        mode=\"explore\",\n        answer=answer,\n        citations=[],\n        map_actions=map_actions,\n        facilities=[],\n    )\n\n\ndef _verify_response(message: str) -> ChatResponse:\n    region = extract_region(message)\n    map_actions = build_map_actions(region)\n    if settings.entities_path.exists():\n        df = pd.read_parquet(settings.entities_path)\n        if region:\n            df = df[df[\"normalized_region\"] == region]\n        flagged = flag_facilities_with_missing_equipment(df.to_dict(\"records\"))\n        flagged = flagged[:10]\n        facility_rows = [\n            {\n                \"pk_unique_id\": row.get(\"pk_unique_id\"),\n                \"name\": row.get(\"name\"),\n                \"lat\": row.get(\"lat\"),\n                \"lng\": row.get(\"lng\"),\n                \"facilityTypeId\": row.get(\"facilityTypeId\"),\n                \"normalized_region\": row.get(\"normalized_region\"),\n                \"address_city\": row.get(\"address_city\"),\n                \"confidence\": row.get(\"confidence\"),\n            }\n            for row in flagged\n        ]\n        facilities = [FacilitySummary(**row) for row in facility_rows if row.get(\"pk_unique_id\")]\n        if flagged:\n            names = \", \".join([row.get(\"name\", \"Unknown\") for row in flagged[:5]])\n            answer = (\n                \"Flagged facilities with potential equipment gaps: \" + names +\n                \". Review each for missing prerequisites.\"\n            )\n        else:\n            answer = \"No obvious equipment gaps detected in the current slice.\"\n        return ChatResponse(\n            mode=\"verify\",\n            answer=answer,\n            citations=[],\n            map_actions=map_actions,\n            facilities=facilities,\n        )\n\n    answer = generate_answer(message, \"verify\")\n    return ChatResponse(\n        mode=\"verify\",\n        answer=answer,\n        citations=[],\n        map_actions=map_actions,\n        facilities=[],\n    )\n\n\ndef _plan_response(message: str) -> ChatResponse:\n    map_actions: List[MapAction] = []\n    if settings.entities_path.exists():\n        warehouse = DuckDbWarehouse()\n        rows = warehouse.query(\n            \"SELECT normalized_region, COUNT(*) as c FROM facilities \"\n            \"WHERE normalized_region IS NOT NULL GROUP BY normalized_region\"\n        )\n        scores = {row[0]: row[1] for row in rows if row[0]}\n        ranked = sorted(scores.items(), key=lambda item: item[1])\n        top = ranked[:3]\n        if top:\n            map_actions = build_map_actions(top[0][0])\n            answer = (\n                \"Top underserved regions by facility count: \"\n                + \", \".join([f\"{region} ({count})\" for region, count in top])\n                + \".\"\n            )\n        else:\n            answer = \"No region data available for planning.\"\n        return ChatResponse(\n            mode=\"plan\",\n            answer=answer,\n            citations=[],\n            map_actions=map_actions,\n            facilities=[],\n        )\n\n    answer = generate_answer(message, \"plan\")\n    return ChatResponse(\n        mode=\"plan\",\n        answer=answer,\n        citations=[],\n        map_actions=[],\n        facilities=[],\n    )\n\n\ndef build_chat_response(message: str) -> ChatResponse:\n    mode = classify_mode(message)\n    if mode == \"verify\":\n        return _verify_response(message)\n    if mode == \"plan\":\n        return _plan_response(message)\n    return _explore_response(message)\n*** End Patch"}В request code = "apply_patch"}```"}
