"""Verifier agent: anomaly detection, compliance, claim validation."""
from __future__ import annotations

from pathlib import Path

from agents import Agent

from agent.tools import make_verifier_tools

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_verifier(G) -> Agent:
    return Agent(
        name="Verifier",
        instructions=(_PROMPTS / "verifier.md").read_text(),
        tools=make_verifier_tools(G),
        model="gpt-5.2",
    )
