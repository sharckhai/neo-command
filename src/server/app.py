"""FastAPI server for VirtueCommand."""
from __future__ import annotations

import json
from typing import AsyncIterator

import pandas as pd
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

from server.agents import init_agents, run_agent_stream
from server.config import settings
from server.models import ChatRequest, FacilitySummary

app = FastAPI(title="VirtueCommand API")


@app.on_event("startup")
async def startup():
    """Initialize knowledge graph and agents."""
    init_agents()


def _format_sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "target": settings.pipeline_target}


@app.get("/api/facilities")
async def facilities() -> list[FacilitySummary]:
    if not settings.entities_path.exists():
        return []
    try:
        df = pd.read_parquet(settings.entities_path)
        subset = df[["pk_unique_id", "name", "lat", "lng", "facilityTypeId",
                      "normalized_region", "address_city", "confidence"]]
        subset = subset.dropna(subset=["lat", "lng"])
        return [FacilitySummary(**row) for row in subset.head(2000).to_dict("records")]
    except Exception:
        return []


@app.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    async def event_generator() -> AsyncIterator[str]:
        async for event in run_agent_stream(request.message, request.session_id):
            yield _format_sse_event(event)

    return EventSourceResponse(event_generator())
