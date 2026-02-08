from agent.tools.resolve_tools import make_resolve_tools
from agent.tools.search_tools import make_search_tools
from agent.tools.inspect_tools import make_inspect_tools
from agent.tools.gap_tools import make_gap_tools
from agent.tools.anomaly_tools import make_anomaly_tools
from agent.tools.overview_tools import make_overview_tools


def make_all_tools(G):
    """Create all 11 agent tools bound to the given graph."""
    return [
        *make_resolve_tools(G),
        *make_search_tools(G),
        *make_inspect_tools(G),
        *make_gap_tools(G),
        *make_anomaly_tools(G),
        *make_overview_tools(G),
    ]


def make_explorer_tools(G):
    """Tools for the Explorer agent: landscape, gaps, distributions."""
    return [
        *make_resolve_tools(G),
        *make_overview_tools(G),
        *_pick(make_search_tools(G), {"count_facilities", "search_raw_text"}),
        *make_gap_tools(G),
    ]


def make_fact_tools(G):
    """Tools for the FactAgent: facility lookups, searches, equipment."""
    return [
        *make_resolve_tools(G),
        *_pick(make_search_tools(G), {"find_facility", "search_facilities"}),
        *make_inspect_tools(G),
    ]


def make_verifier_tools(G):
    """Tools for the Verifier agent: anomalies, compliance, validation."""
    return [
        *make_resolve_tools(G),
        *make_anomaly_tools(G),
        *_pick(make_inspect_tools(G), {"inspect_facility", "get_requirements"}),
        *_pick(make_search_tools(G), {"search_raw_text"}),
    ]


def _pick(tools, names: set):
    """Filter a tool list to only those whose name is in *names*."""
    return [t for t in tools if t.name in names]
