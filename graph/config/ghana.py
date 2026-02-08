"""Ghana-specific configuration: region normalization, geocoding, adjacency, population."""

# ---------------------------------------------------------------------------
# Region normalization: raw address_stateOrRegion values → canonical region key
# ---------------------------------------------------------------------------

# Ghana has 16 official regions (since 2019 split).
# The CSV has ~54 raw variants including nulls, typos, and district names.
# We map them all to canonical lowercase keys.

REGION_NORMALIZATION: dict[str, str] = {
    # Greater Accra
    "greater accra": "greater_accra",
    "greater accra region": "greater_accra",
    "accra": "greater_accra",
    "accra east": "greater_accra",
    "accra north": "greater_accra",
    "east legon": "greater_accra",
    "ga east municipality": "greater_accra",
    "ga east municipality, greater accra region": "greater_accra",
    "ledzokuku-krowor": "greater_accra",
    "tema west municipal": "greater_accra",
    "shai osudoku district, greater accra region": "greater_accra",
    # Ashanti
    "ashanti": "ashanti",
    "ashanti region": "ashanti",
    "asokwa-kumasi": "ashanti",
    "ejisu municipal": "ashanti",
    # Western
    "western": "western",
    "western region": "western",
    "takoradi": "western",
    # Western North
    "western north": "western_north",
    "western north region": "western_north",
    # Central
    "central": "central",
    "central region": "central",
    "central ghana": "central",
    "keea": "central",  # Komenda-Edina-Eguafo-Abirem district
    # Eastern
    "eastern": "eastern",
    "eastern region": "eastern",
    # Volta
    "volta": "volta",
    "volta region": "volta",
    "central tongu district": "volta",
    # Oti
    "oti": "oti",
    "oti region": "oti",
    # Northern
    "northern": "northern",
    "northern region": "northern",
    # Savannah
    "savannah": "savannah",
    # Upper East
    "upper east": "upper_east",
    "upper east region": "upper_east",
    # Upper West
    "upper west": "upper_west",
    "upper west region": "upper_west",
    "sissala west district": "upper_west",
    # Bono
    "bono": "bono",
    # Bono East
    "bono east region": "bono_east",
    "techiman municipal": "bono_east",
    # Ahafo
    "ahafo": "ahafo",
    "ahafo region": "ahafo",
    "ahafo ano south-east": "ashanti",  # Ahafo Ano is in Ashanti
    "dormaa east": "bono",  # Dormaa East is in Bono
    "asutifi south": "ahafo",
    # Brong-Ahafo (pre-2019, now split into Bono, Bono East, Ahafo)
    "brong ahafo": "bono",
    "brong ahafo region": "bono",
    # North East
    "north east": "north_east",
    "north east region": "north_east",
    # Misc
    "sh": "ashanti",  # likely abbreviation
    "ghana": None,  # too vague to assign
}

# City → region mapping for rows where region is null but city is known.
# Based on Ghana geography. Only the most common cities in the dataset.
CITY_TO_REGION: dict[str, str] = {
    "accra": "greater_accra",
    "tema": "greater_accra",
    "ashaiman": "greater_accra",
    "madina": "greater_accra",
    "east legon": "greater_accra",
    "osu": "greater_accra",
    "cantonments": "greater_accra",
    "labone": "greater_accra",
    "airport city": "greater_accra",
    "weija": "greater_accra",
    "kasoa": "central",
    "kumasi": "ashanti",
    "obuasi": "ashanti",
    "ejisu": "ashanti",
    "takoradi": "western",
    "sekondi": "western",
    "tarkwa": "western",
    "cape coast": "central",
    "winneba": "central",
    "koforidua": "eastern",
    "nkawkaw": "eastern",
    "ho": "volta",
    "keta": "volta",
    "tamale": "northern",
    "yendi": "northern",
    "sunyani": "bono",
    "berekum": "bono",
    "dormaa ahenkro": "bono",
    "techiman": "bono_east",
    "atebubu": "bono_east",
    "goaso": "ahafo",
    "bolgatanga": "upper_east",
    "navrongo": "upper_east",
    "wa": "upper_west",
    "damongo": "savannah",
    "dambai": "oti",
    "nalerigu": "north_east",
    "battor": "volta",
    "sefwi wiawso": "western_north",
}

# ---------------------------------------------------------------------------
# Region metadata: population, capital, centroid lat/lng
# ---------------------------------------------------------------------------

# Population from Ghana 2021 Population and Housing Census (GSS)
REGION_METADATA: dict[str, dict] = {
    "greater_accra": {
        "display_name": "Greater Accra",
        "population": 5_455_692,
        "capital": "Accra",
        "lat": 5.6037,
        "lng": -0.1870,
    },
    "ashanti": {
        "display_name": "Ashanti",
        "population": 5_432_485,
        "capital": "Kumasi",
        "lat": 6.6885,
        "lng": -1.6244,
    },
    "western": {
        "display_name": "Western",
        "population": 2_060_585,
        "capital": "Sekondi-Takoradi",
        "lat": 5.0110,
        "lng": -1.9748,
    },
    "western_north": {
        "display_name": "Western North",
        "population": 910_553,
        "capital": "Sefwi Wiawso",
        "lat": 6.2050,
        "lng": -2.4880,
    },
    "central": {
        "display_name": "Central",
        "population": 2_563_228,
        "capital": "Cape Coast",
        "lat": 5.1315,
        "lng": -1.2795,
    },
    "eastern": {
        "display_name": "Eastern",
        "population": 2_916_052,
        "capital": "Koforidua",
        "lat": 6.0939,
        "lng": -0.2577,
    },
    "volta": {
        "display_name": "Volta",
        "population": 1_651_053,
        "capital": "Ho",
        "lat": 6.6000,
        "lng": 0.4700,
    },
    "oti": {
        "display_name": "Oti",
        "population": 759_799,
        "capital": "Dambai",
        "lat": 7.6500,
        "lng": 0.1800,
    },
    "northern": {
        "display_name": "Northern",
        "population": 2_310_939,
        "capital": "Tamale",
        "lat": 9.4008,
        "lng": -0.8393,
    },
    "savannah": {
        "display_name": "Savannah",
        "population": 649_627,
        "capital": "Damongo",
        "lat": 9.0833,
        "lng": -1.8167,
    },
    "north_east": {
        "display_name": "North East",
        "population": 587_791,
        "capital": "Nalerigu",
        "lat": 10.5167,
        "lng": -0.3667,
    },
    "upper_east": {
        "display_name": "Upper East",
        "population": 1_301_226,
        "capital": "Bolgatanga",
        "lat": 10.7864,
        "lng": -0.8513,
    },
    "upper_west": {
        "display_name": "Upper West",
        "population": 901_502,
        "capital": "Wa",
        "lat": 10.0601,
        "lng": -2.5099,
    },
    "bono": {
        "display_name": "Bono",
        "population": 1_208_649,
        "capital": "Sunyani",
        "lat": 7.3350,
        "lng": -2.3266,
    },
    "bono_east": {
        "display_name": "Bono East",
        "population": 1_179_568,
        "capital": "Techiman",
        "lat": 7.5833,
        "lng": -1.9333,
    },
    "ahafo": {
        "display_name": "Ahafo",
        "population": 564_536,
        "capital": "Goaso",
        "lat": 6.8000,
        "lng": -2.5167,
    },
}

# ---------------------------------------------------------------------------
# Region adjacency (for BFS in desert detection)
# ---------------------------------------------------------------------------

REGION_ADJACENCY: dict[str, list[str]] = {
    "greater_accra": ["eastern", "central", "volta"],
    "ashanti": ["bono", "bono_east", "ahafo", "western_north", "western", "central", "eastern"],
    "western": ["western_north", "central", "ashanti"],
    "western_north": ["western", "ashanti", "bono", "ahafo"],
    "central": ["greater_accra", "western", "ashanti", "eastern"],
    "eastern": ["greater_accra", "central", "ashanti", "bono_east", "volta", "oti"],
    "volta": ["greater_accra", "eastern", "oti"],
    "oti": ["volta", "eastern", "bono_east", "northern"],
    "northern": ["oti", "bono_east", "savannah", "north_east"],
    "savannah": ["northern", "bono", "bono_east", "upper_west"],
    "north_east": ["northern", "upper_east"],
    "upper_east": ["north_east", "upper_west"],
    "upper_west": ["upper_east", "savannah"],
    "bono": ["bono_east", "ahafo", "ashanti", "western_north", "savannah"],
    "bono_east": ["bono", "ashanti", "eastern", "oti", "northern", "savannah"],
    "ahafo": ["bono", "ashanti", "western_north"],
}

# ---------------------------------------------------------------------------
# City geocoding (approximate lat/lng for common cities)
# ---------------------------------------------------------------------------

CITY_GEOCODING: dict[str, tuple[float, float]] = {
    "accra": (5.6037, -0.1870),
    "tema": (5.6698, -0.0166),
    "kumasi": (6.6885, -1.6244),
    "takoradi": (4.8845, -1.7554),
    "sekondi": (4.9340, -1.7137),
    "cape coast": (5.1036, -1.2466),
    "tamale": (9.4008, -0.8393),
    "sunyani": (7.3350, -2.3266),
    "koforidua": (6.0939, -0.2577),
    "ho": (6.6000, 0.4700),
    "bolgatanga": (10.7864, -0.8513),
    "wa": (10.0601, -2.5099),
    "techiman": (7.5833, -1.9333),
    "obuasi": (6.2046, -1.6720),
    "tarkwa": (5.3044, -1.9809),
    "ashaiman": (5.6894, -0.0372),
    "madina": (5.6673, -0.1641),
    "east legon": (5.6350, -0.1550),
    "osu": (5.5553, -0.1775),
    "weija": (5.5620, -0.3380),
    "kasoa": (5.5340, -0.4170),
    "winneba": (5.3520, -0.6238),
    "nkawkaw": (6.5520, -0.7670),
    "keta": (5.9174, 0.9896),
    "yendi": (9.4430, -0.0100),
    "berekum": (7.4530, -2.5860),
    "dormaa ahenkro": (7.3530, -2.7830),
    "goaso": (6.8000, -2.5167),
    "damongo": (9.0833, -1.8167),
    "dambai": (8.0700, 0.1800),
    "nalerigu": (10.5167, -0.3667),
    "navrongo": (10.8940, -1.0920),
    "battor": (6.0600, 0.4400),
    "ejisu": (6.6940, -1.4640),
    "sefwi wiawso": (6.2050, -2.4880),
    "atebubu": (7.7530, -0.9830),
}
