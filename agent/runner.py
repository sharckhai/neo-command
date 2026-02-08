"""Entry point: load graph, instantiate Self-RAG agent, run query with streaming."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from agents import Runner
from agents.stream_events import RunItemStreamEvent

from agent.self_rag_agent import create_agent
from graph.export import load_graph


async def run_query(query: str, graph_dir: str = "data") -> str:
    """Load the graph, create the agent, and stream a single query."""
    G = load_graph(graph_dir)
    agent = create_agent(G)

    result = Runner.run_streamed(agent, query)

    print("=" * 60)
    print("AGENT TRACE")
    print("=" * 60)

    async for event in result.stream_events():
        if isinstance(event, RunItemStreamEvent):
            item = event.item
            item_type = item.type if hasattr(item, "type") else type(item).__name__

            if item_type == "tool_call_item":
                call = item.raw_item
                name = call.name if hasattr(call, "name") else "?"
                args = call.arguments if hasattr(call, "arguments") else ""
                # Truncate long args for readability
                args_display = args[:200] + "..." if len(str(args)) > 200 else args
                print(f"\n>> TOOL CALL: {name}")
                print(f"   args: {args_display}")

            elif item_type == "tool_call_output_item":
                output = item.output if hasattr(item, "output") else str(item)
                output_display = str(output)[:300] + "..." if len(str(output)) > 300 else output
                print(f"   << result: {output_display}")

            elif item_type == "message_output_item":
                pass  # final message — we print it below

    print("\n" + "=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60 + "\n")

    return result.final_output


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m agent.runner <query>")
        print('Example: python -m agent.runner "Which facilities in Northern Region perform cesarean sections?"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    graph_dir = "data"

    # Check graph exists
    pickle_path = Path(graph_dir) / "knowledge_graph.gpickle"
    if not pickle_path.exists():
        print(f"Error: Graph not found at {pickle_path}")
        print("Run the graph build step first: python -m graph.build_graph <csv_path>")
        sys.exit(1)

    print(f"Query: {query}\n")

    output = asyncio.run(run_query(query, graph_dir))
    print(output)


if __name__ == "__main__":
    main()
