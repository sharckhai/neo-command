"""Explorer agent: landscape, gaps, distributions, overviews."""
from __future__ import annotations

from pathlib import Path

from agents import Agent

from agent.tools import make_explorer_tools

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_explorer(G) -> Agent:
    return Agent(
        name="Explorer",
        instructions=(_PROMPTS / "explorer.md").read_text(),
        tools=make_explorer_tools(G),
        model="gpt-5.2",
    )
