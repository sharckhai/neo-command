from agent.tools.resolve_tools import make_resolve_tools
from agent.tools.search_tools import make_search_tools
from agent.tools.inspect_tools import make_inspect_tools
from agent.tools.gap_tools import make_gap_tools
from agent.tools.anomaly_tools import make_anomaly_tools
from agent.tools.overview_tools import make_overview_tools


def make_all_tools(G):
    """Create all 11 agent tools bound to the given graph.

    Tools:
        1. resolve_terms      — vocabulary guard / self-RAG entry point
        2. find_facility       — fuzzy facility name lookup
        3. search_facilities   — multi-criteria facility search
        4. count_facilities    — aggregation and distribution
        5. search_raw_text     — free-text fallback
        6. inspect_facility    — deep dive into one facility
        7. get_requirements    — equipment requirements + facility comparison
        8. find_gaps           — deserts, could_support, NGO gaps, compliance
        9. find_cold_spots     — geographic coverage analysis
       10. detect_anomalies    — statistical outlier detection
       11. explore_overview    — national/region/specialty overview
    """
    return [
        *make_resolve_tools(G),
        *make_search_tools(G),
        *make_inspect_tools(G),
        *make_gap_tools(G),
        *make_anomaly_tools(G),
        *make_overview_tools(G),
    ]
