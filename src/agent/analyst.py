"""Analyst agent: landscape overviews, gap analysis, facility details."""
from __future__ import annotations

from pathlib import Path

from agents import Agent

from agent.tools import make_analyst_tools

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_analyst(G) -> Agent:
    instructions = (_PROMPTS / "analyst.md").read_text()
    tools_ref = (_PROMPTS / "tools.md").read_text()
    instructions = instructions.replace("{{tools}}", tools_ref)
    return Agent(
        name="Analyst",
        instructions=instructions,
        tools=make_analyst_tools(G),
        model="gpt-5.2",
    )
