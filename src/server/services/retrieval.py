from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from server.config import settings
from server.data.vector_search import VectorSearchClient
from server.data.vector_store import LocalVectorStore
from server.medical_knowledge import contains_aspirational_language, contains_referral_language
from server.tracing import TraceRecorder


def filter_relevant_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for hit in hits:
        text = str(hit.get("text", ""))
        if contains_referral_language(text) or contains_aspirational_language(text):
            continue
        filtered.append(hit)
    return filtered


def _embed_query(query: str) -> Optional[List[float]]:
    if not settings.openai_api_key:
        return None
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model="text-embedding-3-small", input=[query])
    if not response.data:
        return None
    return response.data[0].embedding


def _search_vectors(embedding: List[float], k: int) -> List[Dict[str, Any]]:
    if settings.is_databricks():
        client = VectorSearchClient()
        return client.search(embedding, k=k)
    store = LocalVectorStore()
    return store.search(embedding, k=k)


def _llm_grade_hits(query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not settings.openai_api_key or not hits:
        return hits
    client = OpenAI(api_key=settings.openai_api_key)
    payload = {
        "query": query,
        "hits": [
            {
                "text": hit.get("text"),
                "field": hit.get("field"),
                "name": hit.get("name"),
            }
            for hit in hits
        ],
    }
    system_prompt = (
        "You grade facility snippets for actual capabilities. "
        "Return JSON with key decisions, a list of objects with index and label. "
        "Labels: supported, referral_only, aspirational, unclear."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    decisions = {item.get("index"): item.get("label") for item in data.get("decisions", [])}
    filtered: List[Dict[str, Any]] = []
    for idx, hit in enumerate(hits):
        label = decisions.get(idx)
        if label in {"referral_only", "aspirational"}:
            continue
        filtered.append(hit)
    return filtered


def self_rag_search(query: str, k: int = 5, trace: Optional[TraceRecorder] = None) -> List[Dict[str, Any]]:
    embedding = _embed_query(query)
    if embedding is None:
        if trace:
            trace.add_step("vector.embed", {"query": query}, {"status": "missing_api_key"})
        return []
    if trace:
        trace.add_step("vector.embed", {"query": query}, {"status": "ok"})
    raw_hits = _search_vectors(embedding, k=k)
    if trace:
        trace.add_step("vector.search", {"k": k}, {"hits": len(raw_hits)})
    filtered = filter_relevant_hits(raw_hits)
    refined = _llm_grade_hits(query, filtered)
    if trace:
        trace.add_step("vector.filter", {"input": len(raw_hits)}, {"output": len(refined)})
    return refined
