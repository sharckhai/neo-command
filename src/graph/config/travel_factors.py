"""Travel-time heuristic multipliers per region.

Simple classification of regions by road quality and urbanization.
Used by the context tool to adjust population-access estimates.
"""

from __future__ import annotations

# Classification: "urban", "peri-urban", "rural", "remote"
# Based on GSS urbanization data and road infrastructure assessments.
#
# Travel multiplier: factor applied to straight-line distance to estimate
# actual travel time.  Urban areas have good roads (1.3x), remote areas
# have poor/unpaved roads (2.5x+).

REGION_TRAVEL_FACTORS: dict[str, dict] = {
    "greater_accra": {
        "classification": "urban",
        "travel_multiplier": 1.3,
        "avg_road_quality": "good",
        "notes": "Dense road network, congestion in Accra",
    },
    "ashanti": {
        "classification": "peri-urban",
        "travel_multiplier": 1.5,
        "avg_road_quality": "good",
        "notes": "Good roads around Kumasi, rural periphery",
    },
    "western": {
        "classification": "peri-urban",
        "travel_multiplier": 1.6,
        "avg_road_quality": "moderate",
        "notes": "Coastal roads fair, mining areas better served",
    },
    "western_north": {
        "classification": "rural",
        "travel_multiplier": 2.0,
        "avg_road_quality": "poor",
        "notes": "Limited paved roads, forested terrain",
    },
    "central": {
        "classification": "peri-urban",
        "travel_multiplier": 1.5,
        "avg_road_quality": "moderate",
        "notes": "Coastal highway good, inland roads mixed",
    },
    "eastern": {
        "classification": "peri-urban",
        "travel_multiplier": 1.6,
        "avg_road_quality": "moderate",
        "notes": "Hilly terrain, roads deteriorate away from Koforidua",
    },
    "volta": {
        "classification": "rural",
        "travel_multiplier": 1.8,
        "avg_road_quality": "moderate",
        "notes": "Lake Volta creates access barriers, eastern border areas remote",
    },
    "oti": {
        "classification": "remote",
        "travel_multiplier": 2.2,
        "avg_road_quality": "poor",
        "notes": "Newly created region, limited infrastructure",
    },
    "northern": {
        "classification": "rural",
        "travel_multiplier": 1.8,
        "avg_road_quality": "moderate",
        "notes": "Tamale well-connected, but vast distances to outlying areas",
    },
    "savannah": {
        "classification": "remote",
        "travel_multiplier": 2.5,
        "avg_road_quality": "poor",
        "notes": "Sparse population, unpaved roads, seasonal flooding",
    },
    "north_east": {
        "classification": "remote",
        "travel_multiplier": 2.3,
        "avg_road_quality": "poor",
        "notes": "Newly created region, limited health infrastructure",
    },
    "upper_east": {
        "classification": "rural",
        "travel_multiplier": 2.0,
        "avg_road_quality": "moderate",
        "notes": "Bolgatanga area accessible, outlying areas difficult",
    },
    "upper_west": {
        "classification": "remote",
        "travel_multiplier": 2.3,
        "avg_road_quality": "poor",
        "notes": "Most isolated region, long distances to referral hospitals",
    },
    "bono": {
        "classification": "peri-urban",
        "travel_multiplier": 1.6,
        "avg_road_quality": "moderate",
        "notes": "Sunyani corridor decent, rural fringes less served",
    },
    "bono_east": {
        "classification": "rural",
        "travel_multiplier": 1.8,
        "avg_road_quality": "moderate",
        "notes": "Techiman well-connected, eastern parts near Oti are remote",
    },
    "ahafo": {
        "classification": "rural",
        "travel_multiplier": 1.9,
        "avg_road_quality": "poor",
        "notes": "Small region, limited road network",
    },
}
