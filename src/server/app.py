from __future__ import annotations

from fastapi import FastAPI

from server.config import settings

app = FastAPI()


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "target": settings.pipeline_target}
