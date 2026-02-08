"""Load DHS subnational and WHO national health indicators from external CSVs.

Parses the downloaded HDX datasets and maps DHS region names to canonical
region keys used by the knowledge graph.
"""

from __future__ import annotations

import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# DHS region names → canonical region keys
# ---------------------------------------------------------------------------

# DHS uses a mix of pre-2022 / post-2022 labels. We map them all to
# our canonical 16-region keys (from ghana.py).  Composite regions
# (e.g. "Northern, Upper West, Upper East") are mapped to the dominant
# region or skipped.

_DHS_REGION_MAP: dict[str, str | None] = {
    # Direct matches (post-2018 regions)
    "ahafo": "ahafo",
    "ashanti": "ashanti",
    "bono": "bono",
    "bono east": "bono_east",
    "central": "central",
    "eastern": "eastern",
    "greater accra": "greater_accra",
    "oti": "oti",
    "upper east": "upper_east",
    "upper west": "upper_west",
    "western north": "western_north",
    # Pre/post-2022 suffixed variants
    "northern (pre 2022)": "northern",
    "northern (post 2022)": "northern",
    "..northern(post 2022)": "northern",
    "volta (pre 2022)": "volta",
    "volta (post 2022)": "volta",
    "western (pre 2022)": "western",
    "western (post 2022)": "western",
    # Sub-regions with .. prefix
    "..northeast": "north_east",
    "..savannah": "savannah",
    # Legacy combined regions (pre-2019 split)
    "brong-ahafo": "bono",  # map to primary successor
    # Too broad to assign
    "northern, upper west, upper east": None,
}


def _normalize_dhs_region(raw: str) -> str | None:
    """Map a DHS Location value to our canonical region key, or None."""
    return _DHS_REGION_MAP.get(raw.strip().lower())


# ---------------------------------------------------------------------------
# CSV directory
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "external" / "health_indicators"


# ---------------------------------------------------------------------------
# Generic DHS CSV reader
# ---------------------------------------------------------------------------

def _read_dhs_csv(filename: str) -> list[dict]:
    """Read a DHS subnational CSV, skipping the HXL tag row."""
    path = _DATA_DIR / filename
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip the HXL tag row (starts with #)
            if row.get("ISO3", "").startswith("#"):
                continue
            rows.append(row)
    return rows


def _latest_by_region(
    rows: list[dict],
    indicator_filter: str | None = None,
) -> dict[str, dict]:
    """Extract the most recent value per indicator per region.

    Returns: {canonical_region: {indicator_name: value, ...}}
    """
    # Track (region, indicator) → (year, value)
    best: dict[tuple[str, str], tuple[int, float]] = {}

    for row in rows:
        region = _normalize_dhs_region(row.get("Location", ""))
        if region is None:
            continue

        indicator = row.get("Indicator", "").strip()
        if indicator_filter and indicator_filter.lower() not in indicator.lower():
            continue

        try:
            year = int(row.get("SurveyYear", 0))
            value = float(row.get("Value", 0))
        except (ValueError, TypeError):
            continue

        key = (region, indicator)
        if key not in best or year > best[key][0]:
            best[key] = (year, value)

    # Reshape to {region: {indicator: value}}
    result: dict[str, dict] = {}
    for (region, indicator), (year, value) in best.items():
        if region not in result:
            result[region] = {"_survey_year": year}
        result[region][indicator] = value
        # Keep the most recent year across all indicators
        if year > result[region].get("_survey_year", 0):
            result[region]["_survey_year"] = year

    return result


# ---------------------------------------------------------------------------
# Per-dataset loaders
# ---------------------------------------------------------------------------

def load_child_mortality() -> dict[str, dict]:
    """Under-5 mortality, infant mortality, neonatal mortality by region."""
    rows = _read_dhs_csv("child-mortality-rates_subnational_gha.csv")
    return _latest_by_region(rows)


def load_healthcare_access() -> dict[str, dict]:
    """Healthcare access barriers by region."""
    rows = _read_dhs_csv("access-to-health-care_subnational_gha.csv")
    return _latest_by_region(rows)


def load_immunization() -> dict[str, dict]:
    """Vaccination coverage (DPT, measles, etc.) by region."""
    rows = _read_dhs_csv("immunization_subnational_gha.csv")
    return _latest_by_region(rows)


def load_health_insurance() -> dict[str, dict]:
    """Insurance coverage by region."""
    rows = _read_dhs_csv("health-insurance_subnational_gha.csv")
    return _latest_by_region(rows)


def load_anemia() -> dict[str, dict]:
    """Anemia prevalence by region."""
    rows = _read_dhs_csv("anemia_subnational_gha.csv")
    return _latest_by_region(rows)


def load_fertility() -> dict[str, dict]:
    """Total fertility rate by region."""
    rows = _read_dhs_csv("fertility-rates_subnational_gha.csv")
    return _latest_by_region(rows)


# ---------------------------------------------------------------------------
# WHO national indicators
# ---------------------------------------------------------------------------

def load_who_health_systems() -> dict[str, float]:
    """National WHO health system indicators (hospital beds, etc.)."""
    path = _DATA_DIR / "health_systems_indicators_gha.csv"
    if not path.exists():
        return {}
    result: dict[str, float] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("GHO (CODE)", "").startswith("#"):
                continue
            indicator = row.get("GHO (DISPLAY)", "").strip()
            try:
                value = float(row.get("Numeric", 0))
            except (ValueError, TypeError):
                continue
            year_str = row.get("YEAR (DISPLAY)", "0")
            try:
                year = int(year_str)
            except ValueError:
                year = 0
            # Keep the latest year per indicator
            if indicator not in result or year > result.get(f"_year_{indicator}", 0):
                result[indicator] = value
                result[f"_year_{indicator}"] = year
    # Clean up year tracking keys
    return {k: v for k, v in result.items() if not k.startswith("_year_")}


# ---------------------------------------------------------------------------
# Unified loader — REGION_HEALTH_INDICATORS
# ---------------------------------------------------------------------------

# Key indicators to extract per region (indicator name → short key)
_KEY_INDICATORS = {
    # Child mortality
    "Under-5 mortality rate": "under5_mortality",
    "Infant mortality rate": "infant_mortality",
    "Neonatal mortality rate": "neonatal_mortality",
    # Immunization
    "Fully vaccinated (8 basic antigens)": "fully_vaccinated_pct",
    "DPT 3 vaccination received": "dpt3_pct",
    "Measles vaccination received": "measles_pct",
    # Anemia
    "Children with any anemia": "child_anemia_pct",
    "Women with any anemia": "women_anemia_pct",
    # Insurance
    "No health insurance [Women]": "no_insurance_women_pct",
    "No health insurance [Men]": "no_insurance_men_pct",
    # Fertility
    "Total fertility rate 15-49": "total_fertility_rate",
    # Healthcare access
    "Delivery by cesarean section": "cesarean_pct",
    "Place of delivery: Health facility": "facility_delivery_pct",
    "Antenatal care from a skilled provider": "skilled_antenatal_pct",
    "Assistance during delivery from a skilled provider": "skilled_delivery_pct",
}


def load_all_indicators() -> dict[str, dict]:
    """Load all DHS subnational indicators into a unified dict.

    Returns:
        {canonical_region: {short_key: value, "_survey_year": year, ...}}
    """
    datasets = [
        load_child_mortality(),
        load_immunization(),
        load_anemia(),
        load_health_insurance(),
        load_fertility(),
        load_healthcare_access(),
    ]

    from graph.config.ghana import REGION_METADATA
    all_regions = set(REGION_METADATA.keys())

    unified: dict[str, dict] = {r: {} for r in all_regions}

    for dataset in datasets:
        for region, indicators in dataset.items():
            if region not in unified:
                continue
            survey_year = indicators.get("_survey_year", 0)
            if survey_year > unified[region].get("_survey_year", 0):
                unified[region]["_survey_year"] = survey_year
            for long_name, short_key in _KEY_INDICATORS.items():
                if long_name in indicators:
                    unified[region][short_key] = indicators[long_name]

    return unified


# ---------------------------------------------------------------------------
# Convenience: print summary
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    indicators = load_all_indicators()
    for region in sorted(indicators):
        data = indicators[region]
        if data:
            print(f"\n{region}:")
            print(json.dumps(data, indent=2))
        else:
            print(f"\n{region}: (no data)")

    print("\n--- WHO National ---")
    who = load_who_health_systems()
    print(json.dumps(who, indent=2))
