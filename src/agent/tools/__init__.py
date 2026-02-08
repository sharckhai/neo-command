from agent.tools.resolve_tools import make_resolve_tools
from agent.tools.search_tools import make_search_tools
from agent.tools.inspect_tools import make_inspect_tools
from agent.tools.gap_tools import make_gap_tools
from agent.tools.anomaly_tools import make_anomaly_tools
from agent.tools.overview_tools import make_overview_tools
from agent.tools.context_tools import make_context_tools
from agent.tools.rag_tools import make_rag_tools


def make_all_tools(G):
    """Create all agent tools bound to the given graph."""
    return [
        *make_resolve_tools(G),
        *make_search_tools(G),
        *make_inspect_tools(G),
        *make_gap_tools(G),
        *make_anomaly_tools(G),
        *make_overview_tools(G),
        *make_context_tools(G),
    ]


def make_analyst_tools(G):
    """Tools for the Analyst agent: landscape + facility details (graph only)."""
    return [
        *make_resolve_tools(G),
        *make_overview_tools(G),
        *make_search_tools(G),
        *make_gap_tools(G),
        *make_inspect_tools(G),
    ]


def make_verifier_tools(G):
    """Tools for the Verifier agent: resolve vocabulary + query LACKS edges."""
    return [
        *make_resolve_tools(G),
        *_pick(make_inspect_tools(G), {"find_lacks"}),
    ]


def make_planner_tools(G):
    """Tools for the Planner agent: region context enrichment only."""
    return [
        *make_context_tools(G),
    ]


def _pick(tools, names: set):
    """Filter a tool list to only those whose name is in *names*."""
    return [t for t in tools if t.name in names]
