# VirtueCommand Product Spec Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the backend and frontend MVP for VirtueCommand (excluding Knowledge Graph / GraphRAG), covering triage, explore/verify/plan modes, SSE streaming, and the map + chat UI.

**Architecture:** Backend-first in a single Python service (FastAPI + OpenAI Agents SDK) with SSE streaming and adapters for SQL + vector search. Frontend is Next.js + Mapbox with a two-panel UI that consumes SSE events and drives map actions. Databricks integrations are optional and gated by env vars; local DuckDB + LanceDB act as defaults.

**Tech Stack:** FastAPI, OpenAI Agents SDK (`openai-agents`), pandas/duckdb, LanceDB, Next.js (App Router), Mapbox GL JS, SSE.

---

## Preconditions
- Work on branch `virtuecommand-pipeline`.
- Use current repo root `c:\Projects\HackNation\Neo`.
- No Knowledge Graph / GraphRAG features.
- Use local DuckDB + LanceDB by default; allow Databricks env-gated wiring.

---

### Task 1: Add backend dependencies + package layout

**Files:**
- Modify: `pyproject.toml`
- Create: `src/server/__init__.py`
- Create: `src/server/config.py`
- Create: `src/server/app.py`
- Create: `tests/server/test_health.py`

**Step 1: Write the failing test**
```python
from fastapi.testclient import TestClient
from server.app import app


def test_health():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_health.py -v`
Expected: FAIL (module not found / endpoint missing)

**Step 3: Write minimal implementation**
- Add dependencies: `fastapi`, `uvicorn`, `sse-starlette`, `openai-agents`, `duckdb`, `httpx`.
- Create `src/server/app.py` with a FastAPI app and `/api/health`.
- Create `src/server/config.py` with env settings (OPENAI_API_KEY, PIPELINE_TARGET, DATABRICKS_*).

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_health.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add pyproject.toml src/server/app.py src/server/config.py tests/server/test_health.py
git commit -m "feat: add backend skeleton and health endpoint"
```

---

### Task 2: Local SQL warehouse adapter (DuckDB)

**Files:**
- Create: `src/server/data/warehouse.py`
- Create: `tests/server/test_warehouse.py`

**Step 1: Write the failing test**
```python
import pandas as pd
from server.data.warehouse import DuckDbWarehouse


def test_duckdb_query(tmp_path):
    df = pd.DataFrame([
        {"pk_unique_id": "1", "name": "Alpha", "normalized_region": "Northern"},
        {"pk_unique_id": "2", "name": "Beta", "normalized_region": "Northern"},
    ])
    parquet = tmp_path / "entities.parquet"
    df.to_parquet(parquet, index=False)

    warehouse = DuckDbWarehouse(entities_path=parquet)
    result = warehouse.query("SELECT COUNT(*) as c FROM facilities")
    assert result[0][0] == 2
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_warehouse.py -v`
Expected: FAIL (module missing)

**Step 3: Write minimal implementation**
- Implement `DuckDbWarehouse` that loads `output/step4_entities.parquet` by default.
- Expose `query(sql: str) -> list[tuple]`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_warehouse.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/server/data/warehouse.py tests/server/test_warehouse.py
git commit -m "feat: add DuckDB warehouse adapter"
```

---

### Task 3: Vector search adapter (LanceDB)

**Files:**
- Create: `src/server/data/vector_store.py`
- Create: `tests/server/test_vector_store.py`

**Step 1: Write the failing test**
```python
import pandas as pd
from server.data.vector_store import LocalVectorStore


def test_local_vector_store_search(tmp_path):
    df = pd.DataFrame([
        {"pk_unique_id": "1", "text": "cataract surgery", "embedding": [0.1] * 1536},
        {"pk_unique_id": "2", "text": "dental cleaning", "embedding": [0.2] * 1536},
    ])
    store = LocalVectorStore(db_path=tmp_path)
    store.upsert(df)
    results = store.search([0.1] * 1536, k=1)
    assert results[0]["pk_unique_id"] == "1"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_vector_store.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
- Implement `LocalVectorStore` with LanceDB.
- Provide `upsert(df)` and `search(embedding, k)`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_vector_store.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/server/data/vector_store.py tests/server/test_vector_store.py
git commit -m "feat: add LanceDB vector search adapter"
```

---

### Task 4: API schemas + map response models

**Files:**
- Create: `src/server/models.py`
- Create: `tests/server/test_models.py`

**Step 1: Write the failing test**
```python
from server.models import ChatRequest, ChatResponse


def test_models_roundtrip():
    req = ChatRequest(message="hello", session_id="abc")
    res = ChatResponse(mode="explore", answer="hi", citations=[])
    assert req.message == "hello"
    assert res.mode == "explore"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_models.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
- Add Pydantic models: `ChatRequest`, `ChatResponse`, `MapAction`, `FacilitySummary`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_models.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/server/models.py tests/server/test_models.py
git commit -m "feat: add API models"
```

---

### Task 5: Medical knowledge heuristics (no KG)

**Files:**
- Create: `src/server/medical_knowledge.py`
- Create: `tests/server/test_medical_knowledge.py`

**Step 1: Write the failing test**
```python
from server.medical_knowledge import required_equipment_for


def test_required_equipment():
    req = required_equipment_for("cataract surgery")
    assert "microscope" in " ".join(req).lower()
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_medical_knowledge.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
- Add a small curated mapping for common procedures -> required equipment keywords.
- Provide helpers for matching equipment and flagging gaps.

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_medical_knowledge.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/server/medical_knowledge.py tests/server/test_medical_knowledge.py
git commit -m "feat: add medical knowledge heuristics"
```

---

### Task 6: Agent tools (SQL + vector + verify + planning)

**Files:**
- Create: `src/server/tools.py`
- Create: `tests/server/test_tools.py`

**Step 1: Write the failing test**
```python
from server.tools import rank_regions_by_gap


def test_rank_regions_by_gap():
    regions = {"Northern": 10, "Ashanti": 50}
    ranking = rank_regions_by_gap(regions)
    assert ranking[0][0] == "Northern"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_tools.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
- Implement tool functions for SQL queries, vector search, verify heuristics, and plan ranking.
- Ensure tools are simple, deterministic, and do not require OpenAI to test.

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_tools.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/server/tools.py tests/server/test_tools.py
git commit -m "feat: add tool functions"
```

---

### Task 7: Agent orchestration (triage + specialized agents)

**Files:**
- Create: `src/server/agents.py`
- Create: `tests/server/test_triage.py`

**Step 1: Write the failing test**
```python
from server.agents import classify_mode


def test_classify_mode_rules():
    assert classify_mode("Which facilities claim surgery but lack equipment?") == "verify"
    assert classify_mode("Where should we deploy?",) == "plan"
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_triage.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
- Add a lightweight rule-based classifier as fallback.
- Wire OpenAI Agents SDK with handoffs and tools. Use `RECOMMENDED_PROMPT_PREFIX` for handoffs.
- For streaming, use `Runner.run_streamed()`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_triage.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/server/agents.py tests/server/test_triage.py
git commit -m "feat: add agent orchestration"
```

---

### Task 8: SSE streaming endpoint

**Files:**
- Modify: `src/server/app.py`
- Create: `tests/server/test_sse.py`

**Step 1: Write the failing test**
```python
from fastapi.testclient import TestClient
from server.app import app


def test_sse_endpoint():
    client = TestClient(app)
    res = client.post("/api/chat", json={"message": "hi", "session_id": "t1"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_sse.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
- Implement `/api/chat` returning an SSE stream of token deltas and final JSON payload.
- Add `/api/facilities` for initial map markers (minimal fields).

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_sse.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/server/app.py tests/server/test_sse.py
git commit -m "feat: add SSE chat endpoint"
```

---

### Task 9: Frontend app scaffold (Next.js + Mapbox)

**Files:**
- Create: `apps/web/` (Next.js project)
- Create: `apps/web/app/page.tsx`
- Create: `apps/web/components/MapPanel.tsx`
- Create: `apps/web/components/ChatPanel.tsx`
- Create: `apps/web/app/globals.css`

**Step 1: Write the failing test**
```tsx
import { render } from "@testing-library/react";
import Home from "../app/page";

test("renders chat input", () => {
  const { getByPlaceholderText } = render(<Home />);
  getByPlaceholderText(/ask/i);
});
```

**Step 2: Run test to verify it fails**
Run: `pnpm test` (or `npm test`) inside `apps/web`
Expected: FAIL

**Step 3: Write minimal implementation**
- Create Next.js app, wire Mapbox map and a two-panel layout.
- Implement SSE client in ChatPanel.
- Apply `@vercel-react-best-practices` when writing React code.

**Step 4: Run test to verify it passes**
Run: `pnpm test`
Expected: PASS

**Step 5: Commit**
```bash
git add apps/web
git commit -m "feat: add Next.js UI scaffold"
```

---

### Task 10: Wire UI to backend events

**Files:**
- Modify: `apps/web/components/ChatPanel.tsx`
- Modify: `apps/web/components/MapPanel.tsx`
- Create: `apps/web/lib/sse.ts`
- Create: `apps/web/lib/types.ts`

**Step 1: Write the failing test**
```tsx
import { parseEventStream } from "../lib/sse";

test("parses event stream chunks", () => {
  const events = parseEventStream("data: {\"type\":\"token\",\"text\":\"hi\"}\n\n");
  expect(events[0].type).toBe("token");
});
```

**Step 2: Run test to verify it fails**
Run: `pnpm test`
Expected: FAIL

**Step 3: Write minimal implementation**
- Parse SSE events into tokens and final payload.
- Apply map actions from the backend (zoom, highlights, facility markers).

**Step 4: Run test to verify it passes**
Run: `pnpm test`
Expected: PASS

**Step 5: Commit**
```bash
git add apps/web
git commit -m "feat: wire chat SSE to map"
```

---

### Task 11: API + UI integration polish

**Files:**
- Modify: `src/server/app.py`
- Modify: `apps/web/components/ChatPanel.tsx`
- Modify: `apps/web/components/MapPanel.tsx`

**Step 1: Write the failing test**
```python
from fastapi.testclient import TestClient
from server.app import app


def test_facilities_endpoint():
    client = TestClient(app)
    res = client.get("/api/facilities")
    assert res.status_code == 200
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/server/test_facilities.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
- Ensure map markers load from backend endpoint.
- Ensure UI has graceful empty states.

**Step 4: Run test to verify it passes**
Run: `pytest tests/server/test_facilities.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/server/app.py apps/web
git commit -m "feat: polish api and ui integration"
```

---

### Task 12: Documentation + scripts

**Files:**
- Modify: `README.md`
- Create: `docs/SETUP.md`

**Step 1: Write the failing test**
- Not applicable; documentation task.

**Step 2: Write minimal implementation**
- Document env vars, run commands, and dataset prerequisites.

**Step 3: Commit**
```bash
git add README.md docs/SETUP.md
git commit -m "docs: add setup instructions"
```

---

## Execution Notes
- Use `@vercel-react-best-practices` when writing React/Next.js code.
- For OpenAI Agents SDK usage, follow official docs for `Agent`, `Runner`, `handoffs`, and `run_streamed` streaming patterns. 
- Avoid GraphRAG and Knowledge Graph features.

---

Plan complete and saved to `docs/plans/2026-02-08-virtuecommand-product-spec-implementation.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open a new session with executing-plans, batch execution with checkpoints

Which approach?
