# VirtueCommand Backend (No FE / No Graph RAG) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver the backend agents, tracing, and Databricks-compatible data adapters described in the spec, excluding frontend and graph RAG.

**Architecture:** Use OpenAI Agents SDK for routing when available, backed by local-first DuckDB + LanceDB adapters with optional Databricks SQL, Genie text-to-SQL, and Vector Search adapters. Add a trace recorder that always returns tool steps and optionally logs to MLflow.

**Tech Stack:** FastAPI, OpenAI Agents SDK, DuckDB, LanceDB, Databricks SQL connector, MLflow, OpenAI embeddings.

---

### Task 1: Add tracing models + config scaffolding

**Files:**
- Create: `src/server/tracing.py`
- Modify: `src/server/models.py:8-34`
- Modify: `src/server/config.py:1-40`
- Modify: `pyproject.toml:7-36`
- Create: `tests/server/test_trace.py`

**Step 1: Write the failing test**

```python
from server.tracing import TraceEvent, TraceRecorder

def test_trace_recorder_captures_steps():
    recorder = TraceRecorder()
    recorder.add_step("sql.query", {"sql": "select 1"}, {"rows": 1})
    trace = recorder.snapshot()
    assert trace[0].name == "sql.query"
    assert trace[0].output["rows"] == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/server/test_trace.py::test_trace_recorder_captures_steps -v`
Expected: FAIL with `ModuleNotFoundError: server.tracing`

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class TraceEvent:
    name: str
    input: Dict[str, Any]
    output: Dict[str, Any]

@dataclass
class TraceRecorder:
    steps: List[TraceEvent] = field(default_factory=list)

    def add_step(self, name: str, input: Dict[str, Any], output: Dict[str, Any]) -> None:
        self.steps.append(TraceEvent(name=name, input=input, output=output))

    def snapshot(self) -> List[TraceEvent]:
        return list(self.steps)
```

Also update `ChatResponse` to include `trace: List[TraceEvent]`, add optional MLflow config fields in `Settings`, and add dependencies for `mlflow` plus Databricks adapters.

```toml
dependencies = [
  ...
  "mlflow",
  "databricks-sdk",
  "databricks-vectorsearch",
]

[project.optional-dependencies]
databricks = [
  "databricks-sql-connector",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/server/test_trace.py::test_trace_recorder_captures_steps -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/server/tracing.py src/server/models.py src/server/config.py tests/server/test_trace.py
git commit -m "feat: add trace recorder and response schema"
```

### Task 2: Databricks SQL + Genie + Vector Search adapters

**Files:**
- Create: `src/server/data/genie.py`
- Create: `src/server/data/vector_search.py`
- Modify: `src/server/data/databricks.py:1-34`
- Create: `tests/server/test_genie.py`
- Create: `tests/server/test_vector_adapter.py`

**Step 1: Write the failing tests**

```python
from server.data.genie import GenieClient


def test_genie_requires_env():
    client = GenieClient()
    try:
        client.generate_sql("count hospitals")
    except RuntimeError as exc:
        assert "Genie" in str(exc)
```

```python
from server.data.vector_search import VectorSearchClient


def test_vector_search_falls_back_to_empty():
    client = VectorSearchClient()
    results = client.search([0.0, 0.0], k=3)
    assert results == []
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/server/test_genie.py::test_genie_requires_env -v`
Expected: FAIL with `ModuleNotFoundError`

Run: `pytest tests/server/test_vector_adapter.py::test_vector_search_falls_back_to_empty -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementations**

```python
class GenieClient:
    def generate_sql(self, prompt: str) -> str:
        raise RuntimeError("Genie is not configured")
```

```python
class VectorSearchClient:
    def search(self, embedding: list[float], k: int = 5) -> list[dict]:
        return []
```

Then extend `databricks.py` with helper methods to build http clients when env vars exist, and wire the adapters to read `DATABRICKS_*` env vars.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/server/test_genie.py::test_genie_requires_env -v`
Expected: PASS

Run: `pytest tests/server/test_vector_adapter.py::test_vector_search_falls_back_to_empty -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/server/data/genie.py src/server/data/vector_search.py src/server/data/databricks.py tests/server/test_genie.py tests/server/test_vector_adapter.py
git commit -m "feat: add databricks genie and vector search adapters"
```

### Task 3: Self-RAG vector retrieval service

**Files:**
- Create: `src/server/services/retrieval.py`
- Modify: `src/server/services/search.py:1-122`
- Create: `tests/server/test_retrieval.py`

**Step 1: Write the failing test**

```python
from server.services.retrieval import filter_relevant_hits


def test_filter_relevant_hits_removes_referrals():
    hits = [
        {"text": "Facility does surgery", "field": "capability"},
        {"text": "We refer surgery cases", "field": "description"},
    ]
    filtered = filter_relevant_hits(hits)
    assert len(filtered) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/server/test_retrieval.py::test_filter_relevant_hits_removes_referrals -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
from server.medical_knowledge import contains_referral_language, contains_aspirational_language

def filter_relevant_hits(hits: list[dict]) -> list[dict]:
    filtered = []
    for hit in hits:
        text = str(hit.get("text", ""))
        if contains_referral_language(text) or contains_aspirational_language(text):
            continue
        filtered.append(hit)
    return filtered
```

Then extend to embed queries with OpenAI, call LanceDB or Databricks Vector Search, and optionally run an LLM grading step if `OPENAI_API_KEY` is present.

**Step 4: Run test to verify it passes**

Run: `pytest tests/server/test_retrieval.py::test_filter_relevant_hits_removes_referrals -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/server/services/retrieval.py src/server/services/search.py tests/server/test_retrieval.py
git commit -m "feat: add self-rag retrieval service"
```

### Task 4: Facility intelligence debate in VERIFY mode

**Files:**
- Modify: `src/server/services/verify.py:1-35`
- Create: `src/server/services/debate.py`
- Create: `tests/server/test_verify_debate.py`

**Step 1: Write the failing test**

```python
from server.services.verify import build_verify_summary


def test_build_verify_summary_includes_flags():
    summary = build_verify_summary("Test Hospital", ["missing_equipment"], 42)
    assert "missing_equipment" in summary
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/server/test_verify_debate.py::test_build_verify_summary_includes_flags -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

```python
def build_verify_summary(name: str, flags: list[str], score: int) -> str:
    flag_text = ", ".join(flags) if flags else "no red flags"
    return f"{name}: {flag_text} (confidence {score}/100)."
```

Then extend `debate.py` with Advocate/Skeptic prompts and wire it in `verify.py` so it runs when an API key is present, otherwise uses heuristic-only summaries.

**Step 4: Run test to verify it passes**

Run: `pytest tests/server/test_verify_debate.py::test_build_verify_summary_includes_flags -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/server/services/verify.py src/server/services/debate.py tests/server/test_verify_debate.py
git commit -m "feat: add advocate skeptic verification summaries"
```

### Task 5: Multi-agent debate in PLAN mode

**Files:**
- Modify: `src/server/services/plan.py:1-16`
- Create: `tests/server/test_plan_debate.py`

**Step 1: Write the failing test**

```python
from server.services.plan import build_plan_brief


def test_build_plan_brief_includes_recommendation():
    brief = build_plan_brief({"Northern": 3, "Ashanti": 8})
    assert "Recommendation" in brief
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/server/test_plan_debate.py::test_build_plan_brief_includes_recommendation -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

```python
def build_plan_brief(region_counts: dict[str, int]) -> str:
    if not region_counts:
        return "No region data available for planning."
    worst = sorted(region_counts.items(), key=lambda item: item[1])[0][0]
    return f"Recommendation: prioritize {worst} based on facility scarcity."
```

Then extend with debate prompts if API key exists, producing coverage/readiness/equity notes per region.

**Step 4: Run test to verify it passes**

Run: `pytest tests/server/test_plan_debate.py::test_build_plan_brief_includes_recommendation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/server/services/plan.py tests/server/test_plan_debate.py
git commit -m "feat: add plan debate brief"
```

### Task 6: OpenAI Agents SDK orchestration

**Files:**
- Modify: `src/server/agents.py:1-292`
- Modify: `src/server/app.py:1-63`
- Create: `tests/server/test_agents_sdk.py`

**Step 1: Write the failing test**

```python
from server.agents import build_chat_response


def test_chat_response_includes_trace():
    res = build_chat_response("How many hospitals?")
    assert hasattr(res, "trace")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/server/test_agents_sdk.py::test_chat_response_includes_trace -v`
Expected: FAIL with `AttributeError`

**Step 3: Write minimal implementation**

```python
from server.tracing import TraceRecorder

recorder = TraceRecorder()
recorder.add_step("routing", {"message": message}, {"mode": mode})
```

Then implement Agents SDK routing (Supervisor + 3 specialist agents) that call the SQL, vector, verify, and plan tools, while falling back to the existing heuristic router if `OPENAI_API_KEY` is missing.

**Step 4: Run test to verify it passes**

Run: `pytest tests/server/test_agents_sdk.py::test_chat_response_includes_trace -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/server/agents.py src/server/app.py tests/server/test_agents_sdk.py
git commit -m "feat: add agents sdk routing with tracing"
```

### Task 7: Databricks upload path in pipeline

**Files:**
- Modify: `src/pipeline/upload.py:1-62`
- Create: `tests/pipeline/test_upload_databricks.py`

**Step 1: Write the failing test**

```python
from pipeline.upload import _upload_databricks


def test_upload_databricks_requires_env():
    try:
        _upload_databricks(None, None)
    except RuntimeError as exc:
        assert "Databricks" in str(exc)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_upload_databricks.py::test_upload_databricks_requires_env -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
def _upload_databricks(entities, embeddings):
    raise RuntimeError("Databricks upload requires configuration")
```

Then implement a Databricks SDK upload path that writes parquet to a DBFS/Volume path, executes SQL to create Delta tables, and triggers Vector Search index creation when credentials exist.

**Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_upload_databricks.py::test_upload_databricks_requires_env -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pipeline/upload.py tests/pipeline/test_upload_databricks.py
git commit -m "feat: add databricks upload option"
```

### Task 8: Full test sweep

**Files:**
- Modify: `tests/server/test_must_have.py:1-60` (if needed for new routing behavior)

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: PASS

**Step 2: Commit any follow-up fixes**

```bash
git add tests/server/test_must_have.py src/server/...
git commit -m "test: stabilize suite after agent upgrades"
```
