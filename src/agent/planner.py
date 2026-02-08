"""Planner agent: resource allocation and mission deployment planning."""
from __future__ import annotations

from pathlib import Path

from agents import Agent

from agent.tools import make_planner_tools

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_planner(G) -> Agent:
    instructions = (_PROMPTS / "planner.md").read_text()
    return Agent(
        name="Planner",
        instructions=instructions,
        tools=make_planner_tools(G),
        model="gpt-5.2",
    )
