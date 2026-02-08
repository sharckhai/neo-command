"""Self-RAG agent definition: wires tools + prompt into the OpenAI Agent SDK."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
from agents import Agent

from agent.tools import make_all_tools

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_prompt() -> str:
    """Load the agent instructions from the markdown prompt files."""
    instructions = (_PROMPTS_DIR / "self-rag-agent.md").read_text()
    tool_docs = (_PROMPTS_DIR / "tools.md").read_text()
    return f"{instructions}\n\n---\n\n{tool_docs}"


def create_agent(G: nx.MultiDiGraph) -> Agent:
    """Create the Self-RAG agent bound to the given knowledge graph."""
    tools = make_all_tools(G)
    instructions = _load_prompt()

    return Agent(
        name="VirtueCommand",
        instructions=instructions,
        tools=tools,
        model="gpt-5.2",
    )
