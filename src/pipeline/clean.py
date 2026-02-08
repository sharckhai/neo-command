from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import pandas as pd

from models.enums import CITY_TO_REGION, GHANA_OFFICIAL_REGIONS, REGION_NORMALIZATION, SOURCE_PRIORITY, SOURCE_TYPE_MAP
from pipeline.paths import DATA_DIR, OUTPUT_DIR

RAW_CSV = DATA_DIR / "Virtue Foundation Ghana v0.3 - Sheet1.csv"
OUTPUT_PARQUET = OUTPUT_DIR / "step1_clean.parquet"

JSON_LIST_COLUMNS = [
    "specialties",
    "procedure",
    "equipment",
    "capability",
    "phone_numbers",
    "websites",
    "affiliationTypeIds",
    "countries",
]

SCALAR_INT_COLUMNS = ["area", "numberDoctors", "capacity", "yearEstablished"]
SCALAR_BOOL_COLUMNS = ["acceptsVolunteers"]

CONFLICT_FIELDS = [
    "facilityTypeId",
    "operatorTypeId",
    "capacity",
    "numberDoctors",
    "area",
    "yearEstablished",
    "address_city",
    "address_stateOrRegion",
    "address_country",
    "officialWebsite",
    "officialPhone",
    "email",
]


def _is_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "null", "none"}:
        return True
    return False


def _normalize_city_key(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "null":
        return ""
    return " ".join(text.split()).lower()


def _normalize_region(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"null", "none", "ghana"}:
        return None
    key = " ".join(text.split()).lower()
    if key in REGION_NORMALIZATION:
        return REGION_NORMALIZATION[key]
    for token, region in [
        ("greater accra", "Greater Accra"),
        ("ashanti", "Ashanti"),
        ("western north", "Western North"),
        ("western", "Western"),
        ("upper west", "Upper West"),
        ("upper east", "Upper East"),
        ("north east", "North East"),
        ("northern", "Northern"),
        ("savannah", "Savannah"),
        ("oti", "Oti"),
        ("volta", "Volta"),
        ("eastern", "Eastern"),
        ("central", "Central"),
        ("bono east", "Bono East"),
        ("bono", "Bono"),
        ("ahafo", "Ahafo"),
    ]:
        if token in key:
            return region
    return None


def _parse_json_list(value: Any, field: str, flags: List[str]) -> List[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text or text.lower() in {"null", "none"}:
        return []
    try:
        data = json.loads(text)
    except Exception:
        flags.append(f"json_parse_error_{field}")
        return []
    if not isinstance(data, list):
        return []
    cleaned: List[str] = []
    for item in data:
        if item is None:
            continue
        item_text = str(item).strip()
        if not item_text or item_text.lower() in {"null", "none"}:
            continue
        cleaned.append(item_text)
    return cleaned


def _parse_int(value: Any) -> int | None:
    if _is_null(value):
        return None
    try:
        return int(float(str(value)))
    except Exception:
        return None


def _parse_bool(value: Any) -> bool | None:
    if _is_null(value):
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _extract_domain(url: Any) -> str:
    if _is_null(url):
        return ""
    text = str(url).strip()
    parsed = urlparse(text)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _derive_source_type(url: Any) -> str:
    domain = _extract_domain(url)
    if not domain:
        return "unknown"
    if domain in SOURCE_TYPE_MAP:
        return SOURCE_TYPE_MAP[domain]
    if domain.endswith(".gov.gh") or domain.endswith(".gov"):
        return "government"
    if "facebook.com" in domain or "fb.com" in domain:
        return "social"
    if "linkedin.com" in domain:
        return "social"
    if domain.endswith(".org") or domain.endswith(".org.gh"):
        return "official"
    if domain.endswith(".com.gh"):
        return "official"
    return "unknown"


def _source_rank(source_type: str) -> int:
    return SOURCE_PRIORITY.get(source_type, SOURCE_PRIORITY["unknown"])


def _majority_vote(values: List[str]) -> str | None:
    cleaned = [v for v in values if not _is_null(v)]
    if not cleaned:
        return None
    counts = Counter([v.strip() for v in cleaned])
    return counts.most_common(1)[0][0]


def _majority_vote_normalized(values: List[str]) -> Tuple[str | None, int]:
    cleaned = [v for v in values if not _is_null(v)]
    if not cleaned:
        return None, 0
    normalized = defaultdict(list)
    for val in cleaned:
        key = " ".join(str(val).split()).lower()
        normalized[key].append(val)
    counts = {k: len(v) for k, v in normalized.items()}
    best_key = max(counts, key=counts.get)
    best_value = Counter(normalized[best_key]).most_common(1)[0][0]
    return best_value, counts[best_key]


def _has_address_in_name(name: str | None, city: str | None, line1: str | None) -> bool:
    if _is_null(name):
        return False
    name_text = str(name).lower()
    for part in [city, line1]:
        if _is_null(part):
            continue
        part_text = str(part).strip().lower()
        if len(part_text) < 4:
            continue
        if part_text in name_text:
            return True
    return False


def _build_city_inference(records: List[Dict[str, Any]]) -> Dict[str, str]:
    counts: Dict[str, Counter] = defaultdict(Counter)
    for rec in records:
        city_key = _normalize_city_key(rec.get("address_city"))
        region = rec.get("normalized_region")
        if city_key and region:
            counts[city_key][region] += 1
    inferred: Dict[str, str] = {}
    for city_key, counter in counts.items():
        inferred[city_key] = counter.most_common(1)[0][0]
    return inferred


def clean(input_path: Path = RAW_CSV, output_path: Path = OUTPUT_PARQUET) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    records = df.to_dict("records")

    for rec in records:
        flags: List[str] = []
        for col in JSON_LIST_COLUMNS:
            rec[col] = _parse_json_list(rec.get(col), col, flags)
        rec["_json_flags"] = flags

        if str(rec.get("facilityTypeId") or "").strip().lower() == "farmacy":
            rec["facilityTypeId"] = "pharmacy"

        for col in SCALAR_INT_COLUMNS:
            rec[col] = _parse_int(rec.get(col))
        for col in SCALAR_BOOL_COLUMNS:
            rec[col] = _parse_bool(rec.get(col))

        for col in list(rec.keys()):
            if col in JSON_LIST_COLUMNS or col in SCALAR_INT_COLUMNS or col in SCALAR_BOOL_COLUMNS:
                continue
            if _is_null(rec.get(col)):
                rec[col] = None

        rec["source_type"] = _derive_source_type(rec.get("source_url"))
        rec["source_rank"] = _source_rank(rec["source_type"])
        rec["normalized_region"] = _normalize_region(rec.get("address_stateOrRegion"))

    city_inferred = _build_city_inference(records)

    for rec in records:
        if rec.get("normalized_region") is None:
            city_key = _normalize_city_key(rec.get("address_city"))
            if city_key in CITY_TO_REGION:
                rec["normalized_region"] = CITY_TO_REGION[city_key]
            elif city_key in city_inferred:
                rec["normalized_region"] = city_inferred[city_key]

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        pk = rec.get("pk_unique_id")
        if pk is None:
            continue
        grouped[str(pk)].append(rec)

    merged_records: List[Dict[str, Any]] = []

    list_fields = JSON_LIST_COLUMNS

    for pk, group in grouped.items():
        group_sorted = sorted(
            group,
            key=lambda r: (r.get("source_rank", SOURCE_PRIORITY["unknown"]), -sum(1 for v in r.values() if not _is_null(v))),
        )

        merged: Dict[str, Any] = {"pk_unique_id": pk}

        source_urls = [g.get("source_url") for g in group if not _is_null(g.get("source_url"))]
        merged["source_urls"] = sorted(set(source_urls)) if source_urls else []

        source_types = [g.get("source_type") for g in group if not _is_null(g.get("source_type"))]
        merged["source_types"] = sorted(set(source_types)) if source_types else []

        merged["source_count"] = len(group)

        name_value, _ = _majority_vote_normalized([g.get("name") for g in group])
        merged["name"] = name_value

        for field in list_fields:
            values: List[str] = []
            for g in group:
                values.extend(g.get(field) or [])
            deduped = sorted({v.strip() for v in values if v and v.strip()})
            merged[field] = deduped

        for field in df.columns:
            if field in list_fields:
                continue
            if field == "pk_unique_id":
                continue
            if field.startswith("_"):
                continue
            if field in merged:
                continue
            for row in group_sorted:
                value = row.get(field)
                if not _is_null(value):
                    merged[field] = value
                    break
            else:
                merged[field] = None

        region_values = [g.get("normalized_region") for g in group if g.get("normalized_region")]
        merged["normalized_region"] = _majority_vote(region_values) if region_values else None

        flags: List[str] = []
        if merged["source_count"] == 1:
            flags.append("single_source")

        name_variants = {str(g.get("name")).strip().lower() for g in group if not _is_null(g.get("name"))}
        if len(name_variants) > 2:
            flags.append("multi_entity_risk")

        if _has_address_in_name(merged.get("name"), merged.get("address_city"), merged.get("address_line1")):
            flags.append("name_contains_address")

        if merged.get("normalized_region") is None or merged.get("normalized_region") not in GHANA_OFFICIAL_REGIONS:
            flags.append("region_unknown")

        if any("brong ahafo" in str(g.get("address_stateOrRegion") or "").lower() for g in group):
            flags.append("region_legacy_brong_ahafo")

        for field in CONFLICT_FIELDS:
            values = {str(g.get(field)).strip() for g in group if not _is_null(g.get(field))}
            if len(values) > 1:
                flags.append(f"conflict_{field}")

        json_flags = []
        for g in group:
            json_flags.extend(g.get("_json_flags") or [])
        flags.extend(sorted(set(json_flags)))

        merged["quality_flags"] = sorted(set(flags))
        merged["confidence"] = None
        merged["fingerprint"] = None

        merged_records.append(merged)

    merged_df = pd.DataFrame(merged_records)
    merged_df.to_parquet(output_path, index=False)
    return output_path


if __name__ == "__main__":
    clean()
