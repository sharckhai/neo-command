from agent.tools.explore_tools import make_explore_tools
from agent.tools.graph_tools import make_graph_tools
from agent.tools.text_tools import make_text_tools
from agent.tools.vocab_tools import make_vocab_tools


def make_all_tools(G):
    """Create all agent tools bound to the given graph."""
    return [
        *make_graph_tools(G),
        *make_text_tools(G),
        *make_vocab_tools(),
        *make_explore_tools(G),
    ]
