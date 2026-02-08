from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from rich.progress import Progress
from tenacity import retry, stop_after_attempt, wait_exponential

from models.enums import SOURCE_PRIORITY
from pipeline.paths import OUTPUT_DIR

INPUT_PARQUET = OUTPUT_DIR / "step2_geocoded.parquet"
OUTPUT_PARQUET = OUTPUT_DIR / "step3_fingerprinted.parquet"


def _base_fingerprint() -> Dict[str, Any]:
    return {
        "capability_summary": "insufficient data",
        "verified_capabilities": [],
        "anomaly_flags": ["insufficient_data"],
        "upgrade_potential": None,
        "service_permanence": None,
    }


def _compute_confidence(row: Dict[str, Any], fingerprint: Dict[str, Any]) -> float:
    score = 50.0
    source_count = row.get("source_count") or 1
    score += min(source_count * 5.0, 20.0)

    source_types = _to_list(row.get("source_types"))
    if source_types:
        best_rank = min(SOURCE_PRIORITY.get(t, 5) for t in source_types)
        if best_rank <= 2:
            score += 10.0
        elif best_rank == 3:
            score += 5.0
    else:
        score -= 5.0

    verified = fingerprint.get("verified_capabilities") or []
    score += min(len(verified) * 3.0, 20.0)

    anomaly_count = len(fingerprint.get("anomaly_flags") or [])
    score -= min(anomaly_count * 5.0, 25.0)

    if source_count == 1:
        score -= 10.0

    summary = fingerprint.get("capability_summary") or ""
    if "insufficient" in summary.lower():
        score -= 10.0

    return float(max(0.0, min(100.0, score)))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def _fingerprint_llm(client: OpenAI, payload: str) -> Dict[str, Any]:
    system_prompt = (
        "You analyze facility evidence and produce a JSON fingerprint. "
        "Return JSON with keys: capability_summary, verified_capabilities, anomaly_flags, "
        "upgrade_potential, service_permanence. "
        "verified_capabilities must be a list of objects with keys statement and confidence. "
        "confidence is between 0 and 1. Use empty lists when unknown."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    return data


def _has_items(val: Any) -> bool:
    """Check if a value has meaningful content, handling numpy arrays."""
    if val is None:
        return False
    if isinstance(val, np.ndarray):
        return len(val) > 0
    if isinstance(val, (list, tuple)):
        return len(val) > 0
    if isinstance(val, str):
        return bool(val.strip())
    return bool(val)


def _to_list(val: Any) -> list:
    """Convert a value to a Python list, handling numpy arrays."""
    if val is None:
        return []
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, list):
        return val
    return []


def _build_payload(row: Dict[str, Any]) -> str:
    parts: List[str] = []
    for field in [
        "name",
        "facilityTypeId",
        "operatorTypeId",
        "address_city",
        "normalized_region",
    ]:
        value = row.get(field)
        if value and isinstance(value, str):
            parts.append(f"{field}: {value}")

    for field in ["description"]:
        value = row.get(field)
        if value and isinstance(value, str):
            parts.append(f"{field}: {value}")

    for field in ["procedure", "equipment", "capability", "specialties"]:
        items = _to_list(row.get(field))
        if items:
            parts.append(f"{field}: {', '.join(str(i) for i in items)}")

    return "\n".join(parts)


def fingerprint(input_path: Path = INPUT_PARQUET, output_path: Path = OUTPUT_PARQUET) -> Path:
    load_dotenv()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(input_path)
    records = df.to_dict("records")

    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key) if api_key else None

    to_process = []
    for idx, row in enumerate(records):
        has_data = any(_has_items(row.get(field)) for field in ["procedure", "equipment", "capability"])
        if not has_data:
            fingerprint = _base_fingerprint()
            row["fingerprint"] = json.dumps(fingerprint, ensure_ascii=True)
            row["confidence"] = _compute_confidence(row, fingerprint)
        else:
            to_process.append(idx)

    if client and to_process:
        with Progress() as progress:
            task = progress.add_task("Fingerprinting", total=len(to_process))
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {}
                for idx in to_process:
                    payload = _build_payload(records[idx])
                    futures[executor.submit(_fingerprint_llm, client, payload)] = idx
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        fingerprint = future.result()
                    except Exception:
                        fingerprint = _base_fingerprint()
                        fingerprint["anomaly_flags"].append("llm_error")
                    records[idx]["fingerprint"] = json.dumps(fingerprint, ensure_ascii=True)
                    records[idx]["confidence"] = _compute_confidence(records[idx], fingerprint)
                    progress.advance(task)
    else:
        for idx in to_process:
            fingerprint = _base_fingerprint()
            fingerprint["anomaly_flags"].append("no_api_key")
            records[idx]["fingerprint"] = json.dumps(fingerprint, ensure_ascii=True)
            records[idx]["confidence"] = _compute_confidence(records[idx], fingerprint)

    out_df = pd.DataFrame(records)
    out_df.to_parquet(output_path, index=False)
    return output_path


if __name__ == "__main__":
    fingerprint()
