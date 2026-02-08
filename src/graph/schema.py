"""Node and edge type constants and attribute schemas for the knowledge graph."""

# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------

NODE_REGION = "Region"
NODE_FACILITY = "Facility"
NODE_NGO = "NGO"
NODE_CAPABILITY = "Capability"
NODE_EQUIPMENT = "Equipment"
NODE_SPECIALTY = "Specialty"

ALL_NODE_TYPES = {
    NODE_REGION,
    NODE_FACILITY,
    NODE_NGO,
    NODE_CAPABILITY,
    NODE_EQUIPMENT,
    NODE_SPECIALTY,
}

# ---------------------------------------------------------------------------
# Edge types
# ---------------------------------------------------------------------------

EDGE_LOCATED_IN = "LOCATED_IN"
EDGE_HAS_CAPABILITY = "HAS_CAPABILITY"
EDGE_HAS_EQUIPMENT = "HAS_EQUIPMENT"
EDGE_HAS_SPECIALTY = "HAS_SPECIALTY"
EDGE_LACKS = "LACKS"
EDGE_COULD_SUPPORT = "COULD_SUPPORT"
EDGE_DESERT_FOR = "DESERT_FOR"
EDGE_OPERATES_IN = "OPERATES_IN"

ALL_EDGE_TYPES = {
    EDGE_LOCATED_IN,
    EDGE_HAS_CAPABILITY,
    EDGE_HAS_EQUIPMENT,
    EDGE_HAS_SPECIALTY,
    EDGE_LACKS,
    EDGE_COULD_SUPPORT,
    EDGE_DESERT_FOR,
    EDGE_OPERATES_IN,
}

# ---------------------------------------------------------------------------
# Node ID helpers
# ---------------------------------------------------------------------------


def region_id(name: str) -> str:
    """e.g. 'region::northern'"""
    return f"region::{name.lower().strip()}"


def facility_id(pk: str | int) -> str:
    """e.g. 'facility::42'"""
    return f"facility::{pk}"


def ngo_id(pk: str | int) -> str:
    """e.g. 'ngo::105'"""
    return f"ngo::{pk}"


def capability_id(canonical: str) -> str:
    """e.g. 'capability::cataract_surgery'"""
    return f"capability::{canonical}"


def equipment_id(canonical: str) -> str:
    """e.g. 'equipment::operating_microscope'"""
    return f"equipment::{canonical}"


def specialty_id(name: str) -> str:
    """e.g. 'specialty::ophthalmology'"""
    return f"specialty::{name}"


# ---------------------------------------------------------------------------
# Capability categories and complexity
# ---------------------------------------------------------------------------

CAPABILITY_CATEGORIES = {"surgical", "diagnostic", "emergency", "maternity", "therapeutic", "general"}
CAPABILITY_COMPLEXITY = {"low", "medium", "high"}

# ---------------------------------------------------------------------------
# Equipment categories
# ---------------------------------------------------------------------------

EQUIPMENT_CATEGORIES = {"surgical", "imaging", "lab", "infrastructure", "monitoring", "therapeutic"}
