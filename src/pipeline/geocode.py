from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from rich.progress import Progress
from tenacity import retry, stop_after_attempt, wait_exponential

from models.enums import CITY_TO_REGION, GHANA_CITY_COORDS, REGION_CAPITALS
from pipeline.paths import OUTPUT_DIR

INPUT_PARQUET = OUTPUT_DIR / "step1_clean.parquet"
OUTPUT_PARQUET = OUTPUT_DIR / "step2_geocoded.parquet"
CITY_CACHE_PATH = OUTPUT_DIR / "ghana_city_coords.json"


def _normalize_city_key(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "null":
        return ""
    return " ".join(text.split()).lower()


def _load_city_coords() -> Dict[str, Tuple[float, float]]:
    coords = dict(GHANA_CITY_COORDS)
    if CITY_CACHE_PATH.exists():
        try:
            data = json.loads(CITY_CACHE_PATH.read_text(encoding="utf-8"))
            for key, pair in data.items():
                if isinstance(pair, list) and len(pair) == 2:
                    coords[key] = (float(pair[0]), float(pair[1]))
        except Exception:
            pass
    return coords


def _save_city_coords(coords: Dict[str, Tuple[float, float]]) -> None:
    payload = {k: [v[0], v[1]] for k, v in coords.items()}
    CITY_CACHE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _fetch_city_coords(city: str) -> Optional[Tuple[float, float]]:
    query = quote(f"{city}, Ghana")
    url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={query}"
    req = Request(url, headers={"User-Agent": "virtuecommand-pipeline/1.0"})
    with urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload:
        return None
    result = payload[0]
    return float(result["lat"]), float(result["lon"])


def _maybe_fetch_city(city_key: str, coords: Dict[str, Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    if not os.getenv("PIPELINE_GEO_FETCH"):
        return None
    if city_key in coords:
        return coords[city_key]
    time.sleep(1)
    coords_value = _fetch_city_coords(city_key)
    if coords_value:
        coords[city_key] = coords_value
        _save_city_coords(coords)
    return coords_value


def _lookup_region_coords(normalized_region: Optional[str], coords: Dict[str, Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    if not normalized_region:
        return None
    capital = REGION_CAPITALS.get(normalized_region)
    if not capital:
        return None
    capital_key = _normalize_city_key(capital)
    return coords.get(capital_key) or _maybe_fetch_city(capital_key, coords)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def _extract_city_llm(client: OpenAI, text: str) -> Optional[str]:
    system_prompt = (
        "Extract a Ghana city or town name from the text. "
        "Return JSON with a single key city. "
        "Use null if no city is mentioned."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    city = data.get("city")
    if city is None:
        return None
    city_text = str(city).strip()
    return city_text or None


def _build_city_prompt(row: dict) -> str:
    parts: List[str] = []
    for field in [
        "name",
        "description",
        "address_line1",
        "address_line2",
        "address_line3",
        "address_stateOrRegion",
    ]:
        value = row.get(field)
        if value:
            parts.append(f"{field}: {value}")
    for field in ["procedure", "equipment", "capability"]:
        items = row.get(field) or []
        if items:
            parts.append(f"{field}: {', '.join(items)}")
    return "\n".join(parts)


def geocode(input_path: Path = INPUT_PARQUET, output_path: Path = OUTPUT_PARQUET) -> Path:
    load_dotenv()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(input_path)
    records = df.to_dict("records")

    coords = _load_city_coords()

    missing_city_indices = []
    for idx, row in enumerate(records):
        city_key = _normalize_city_key(row.get("address_city"))
        if not city_key:
            missing_city_indices.append(idx)

    extracted_cities: Dict[int, Optional[str]] = {}
    api_key = os.getenv("OPENAI_API_KEY")
    if missing_city_indices and api_key:
        client = OpenAI(api_key=api_key)
        with Progress() as progress:
            task = progress.add_task("Extracting cities", total=len(missing_city_indices))
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {}
                for idx in missing_city_indices:
                    prompt = _build_city_prompt(records[idx])
                    futures[executor.submit(_extract_city_llm, client, prompt)] = idx
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        extracted_cities[idx] = future.result()
                    except Exception:
                        extracted_cities[idx] = None
                    progress.advance(task)

    for idx, row in enumerate(records):
        city_key = _normalize_city_key(row.get("address_city"))
        confidence = "unknown"
        lat = None
        lng = None

        if not city_key and idx in extracted_cities:
            extracted = extracted_cities[idx]
            if extracted:
                row["address_city"] = extracted
                city_key = _normalize_city_key(extracted)
                confidence = "extracted"

        if city_key:
            coords_value = coords.get(city_key) or _maybe_fetch_city(city_key, coords)
            if coords_value:
                lat, lng = coords_value
                confidence = "city" if confidence == "unknown" else confidence

        if lat is None or lng is None:
            normalized_region = row.get("normalized_region")
            if not normalized_region and city_key in CITY_TO_REGION:
                normalized_region = CITY_TO_REGION[city_key]
            region_coords = _lookup_region_coords(normalized_region, coords)
            if region_coords:
                lat, lng = region_coords
                confidence = "region"

        row["lat"] = lat
        row["lng"] = lng
        row["geocode_confidence"] = confidence

    out_df = pd.DataFrame(records)
    out_df.to_parquet(output_path, index=False)
    return output_path


if __name__ == "__main__":
    geocode()
