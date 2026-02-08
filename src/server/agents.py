from __future__ import annotations

from typing import Iterable, List, Optional

from openai import OpenAI

from models.enums import GHANA_OFFICIAL_REGIONS
from server.config import settings
from server.models import ChatResponse, MapAction


VERIFY_KEYWORDS = ["suspicious", "verify", "trust", "claim", "mismatch", "real", "credible", "lack", "missing"]
PLAN_KEYWORDS = ["deploy", "send", "mission", "where should", "recommend", "prioritize", "plan"]


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


def build_chat_response(message: str) -> ChatResponse:
    mode = classify_mode(message)
    region = extract_region(message)
    answer = generate_answer(message, mode)
    map_actions = build_map_actions(region)
    return ChatResponse(mode=mode, answer=answer, citations=[], map_actions=map_actions, facilities=[])
