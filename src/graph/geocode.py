"""Facility geocoding: Nominatim lookups with persistent JSON cache.

Multi-tier resolution per facility:
  1. Cache hit (data/geocode_cache.json keyed by pk_unique_id)
  2. Full address via Nominatim ("{address_line1}, {city}, Ghana")
  3. Name + city via Nominatim ("{facility_name}, {city}, Ghana")
  4. City centroid fallback (CITY_GEOCODING in ghana.py)

Rate-limited: 1 req/sec per Nominatim TOS.
First build ~12 min for ~742 facilities. All cached after that.
"""

from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_PATH = Path("data/geocode_cache.json")


# ---------------------------------------------------------------------------
# Haversine distance (km)
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def _load_cache() -> dict[str, list[float]]:
    """Load geocode cache. Returns {pk: [lat, lng]}."""
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache(cache: dict[str, list[float]]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Nominatim helpers
# ---------------------------------------------------------------------------

def _nominatim_query(query: str) -> tuple[float, float] | None:
    """Query Nominatim for a single address string. Returns (lat, lng) or None."""
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError

    geolocator = Nominatim(user_agent="virtue-command-geocoder")
    try:
        location = geolocator.geocode(query, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning("Nominatim error for %r: %s", query, e)
    return None


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def geocode_facility(
    entity: dict[str, Any],
    country_config: Any,
) -> tuple[float, float] | None:
    """Multi-tier geocode for a single facility entity.

    Tries in order:
      1. Full address via Nominatim
      2. Name + city via Nominatim
      3. City centroid fallback from country_config.CITY_GEOCODING

    Note: cache is handled by batch_geocode(); this function always hits Nominatim.
    """
    address_line1 = entity.get("address_line1")
    city = entity.get("address_city")
    name = entity.get("name")
    country = "Ghana"
    city_geocoding = getattr(country_config, "CITY_GEOCODING", {})
    city_to_region = getattr(country_config, "CITY_TO_REGION", {})
    region_metadata = getattr(country_config, "REGION_METADATA", {})

    city_key = city.lower().strip() if city else None

    def _city_coords() -> tuple[float, float] | None:
        """City centroid from config, or region centroid via CITY_TO_REGION."""
        if not city_key:
            return None
        # Direct city coords
        coords = city_geocoding.get(city_key)
        if coords:
            return coords
        # Neighborhood/suburb → region → region centroid
        region = city_to_region.get(city_key)
        if region and region in region_metadata:
            meta = region_metadata[region]
            return (meta["lat"], meta["lng"])
        return None

    # Tier 1: City/neighborhood in config (instant)
    config_coords = _city_coords()

    # No street address → use config coords or Nominatim city lookup
    if not address_line1:
        if config_coords:
            return config_coords
        if city:
            result = _nominatim_query(f"{city}, {country}")
            if result:
                return result
            time.sleep(1)
        return None

    # Has street address → try Nominatim for street-level, fallback to config
    if city:
        query = f"{address_line1}, {city}, {country}"
        result = _nominatim_query(query)
        if result:
            return result
        time.sleep(1)

        if config_coords:
            return config_coords

    return None


def region_from_coords(
    lat: float,
    lng: float,
    country_config: Any,
) -> str | None:
    """Assign a region key by nearest centroid using haversine distance.

    Uses REGION_METADATA centroids from the country config.
    """
    region_metadata = getattr(country_config, "REGION_METADATA", {})
    if not region_metadata:
        return None

    best_region = None
    best_dist = float("inf")

    for region_key, meta in region_metadata.items():
        rlat = meta.get("lat")
        rlng = meta.get("lng")
        if rlat is None or rlng is None:
            continue
        dist = _haversine_km(lat, lng, rlat, rlng)
        if dist < best_dist:
            best_dist = dist
            best_region = region_key

    return best_region


def batch_geocode(
    rows: list[dict[str, Any]],
    country_config: Any,
) -> dict[str, tuple[float, float]]:
    """Batch geocode all rows with caching.

    Returns dict mapping pk_unique_id → (lat, lng).
    Saves cache to data/geocode_cache.json after processing.
    """
    cache = _load_cache()
    results: dict[str, tuple[float, float]] = {}
    nominatim_calls = 0
    cache_hits = 0
    city_fallbacks = 0
    failed = 0
    total = sum(1 for r in rows if r.get("pk_unique_id"))

    for i, row in enumerate(rows):
        pk = row.get("pk_unique_id")
        if not pk:
            continue

        # Check cache first
        if pk in cache:
            coords = cache[pk]
            results[pk] = (coords[0], coords[1])
            cache_hits += 1
            continue

        # Geocode
        name = row.get("name", "?")
        city = row.get("address_city", "?")
        coords = geocode_facility(row, country_config)
        if coords:
            cache[pk] = [coords[0], coords[1]]
            results[pk] = coords
            # Check if it was a city fallback (no Nominatim call)
            city_geocoding = getattr(country_config, "CITY_GEOCODING", {})
            city_key = (row.get("address_city") or "").lower().strip()
            if city_key and city_geocoding.get(city_key) == coords:
                city_fallbacks += 1
                print(f"  [{cache_hits + nominatim_calls + city_fallbacks + failed}/{total}] {name} ({city}) -> city centroid {coords}")
            else:
                nominatim_calls += 1
                print(f"  [{cache_hits + nominatim_calls + city_fallbacks + failed}/{total}] {name} ({city}) -> nominatim {coords}")
        else:
            failed += 1
            print(f"  [{cache_hits + nominatim_calls + city_fallbacks + failed}/{total}] {name} ({city}) -> FAILED")

    _save_cache(cache)
    print(f"\nGeocoding done: {len(results)}/{total} resolved "
          f"(cache={cache_hits}, nominatim={nominatim_calls}, city={city_fallbacks}, failed={failed})")
    logger.info(
        "Geocoded %d/%d facilities (%d Nominatim lookups, %d from cache)",
        len(results),
        len(rows),
        nominatim_calls,
        len(results) - nominatim_calls if len(results) > nominatim_calls else 0,
    )

    return results
