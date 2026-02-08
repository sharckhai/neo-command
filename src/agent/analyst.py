"""Analyst agent: landscape overviews, gap analysis, facility details."""
from __future__ import annotations

from pathlib import Path

from agents import Agent

from agent.tools import make_analyst_tools

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_analyst(G) -> Agent:
    return Agent(
        name="Analyst",
        instructions=(_PROMPTS / "analyst.md").read_text(),
        tools=make_analyst_tools(G),
        model="gpt-5.2",
    )
