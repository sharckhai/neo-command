"""Verifier agent: anomaly detection, compliance, claim validation."""
from __future__ import annotations

from pathlib import Path

from agents import Agent

from agent.tools import make_verifier_tools

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_verifier(G) -> Agent:
    instructions = (_PROMPTS / "verifier.md").read_text()
    tools_ref = (_PROMPTS / "verifier-tools.md").read_text()
    instructions = instructions.replace("{{tools}}", tools_ref)
    return Agent(
        name="Verifier",
        instructions=instructions,
        tools=make_verifier_tools(G),
        model="gpt-5.2",
    )
