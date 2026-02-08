"""RAG agent: answers questions from uploaded documents."""
from __future__ import annotations

from pathlib import Path

from agents import Agent

from agent.tools.rag_tools import make_rag_tools

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_rag_agent() -> Agent:
    return Agent(
        name="RAGAgent",
        instructions=(_PROMPTS / "rag-agent.md").read_text(),
        tools=make_rag_tools(),
        model="gpt-5.2",
    )
