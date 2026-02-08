"""FactAgent: facility details, lookups, searches, equipment checks."""
from __future__ import annotations

from pathlib import Path

from agents import Agent

from agent.tools import make_fact_tools

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_fact_agent(G) -> Agent:
    return Agent(
        name="FactAgent",
        instructions=(_PROMPTS / "fact-agent.md").read_text(),
        tools=make_fact_tools(G),
        model="gpt-5.2",
    )
