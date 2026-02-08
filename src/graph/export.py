"""Save and load the knowledge graph."""

from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

logger = logging.getLogger(__name__)


def save_graph(G: nx.MultiDiGraph, output_dir: str | Path = "data") -> dict[str, str]:
    """Save the graph in multiple formats.

    Outputs:
        - knowledge_graph.gpickle: Fast loading for runtime
        - knowledge_graph.graphml: For debugging/visualization in Gephi
        - knowledge_graph_meta.json: Node/edge counts, build timestamp

    Returns dict of output file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {}

    # Pickle
    pickle_path = output_dir / "knowledge_graph.gpickle"
    with open(pickle_path, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    paths["pickle"] = str(pickle_path)
    logger.info("Saved pickle: %s", pickle_path)

    # GraphML (needs attribute cleanup — GraphML only supports simple types)
    graphml_path = output_dir / "knowledge_graph.graphml"
    try:
        G_clean = _prepare_for_graphml(G)
        nx.write_graphml(G_clean, str(graphml_path))
        paths["graphml"] = str(graphml_path)
        logger.info("Saved GraphML: %s", graphml_path)
    except Exception as e:
        logger.warning("Failed to save GraphML: %s", e)

    # Metadata JSON
    node_counts: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        nt = data.get("node_type", "unknown")
        node_counts[nt] = node_counts.get(nt, 0) + 1

    edge_counts: dict[str, int] = {}
    for _, _, data in G.edges(data=True):
        et = data.get("edge_type", "unknown")
        edge_counts[et] = edge_counts.get(et, 0) + 1

    meta = {
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "node_counts": node_counts,
        "edge_counts": edge_counts,
    }
    meta_path = output_dir / "knowledge_graph_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    paths["meta"] = str(meta_path)
    logger.info("Saved metadata: %s", meta_path)

    return paths


def load_graph(input_dir: str | Path = "data") -> nx.MultiDiGraph:
    """Load graph from pickle file."""
    pickle_path = Path(input_dir) / "knowledge_graph.gpickle"
    with open(pickle_path, "rb") as f:
        G = pickle.load(f)
    logger.info(
        "Loaded graph: %d nodes, %d edges",
        G.number_of_nodes(), G.number_of_edges(),
    )
    return G


def _prepare_for_graphml(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Create a copy with GraphML-compatible attributes (strings, ints, floats only)."""
    G_clean = nx.MultiDiGraph()

    for nid, data in G.nodes(data=True):
        clean_data = {}
        for k, v in data.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                clean_data[k] = v
            elif isinstance(v, list):
                clean_data[k] = json.dumps(v)
            else:
                clean_data[k] = str(v)
        G_clean.add_node(nid, **clean_data)

    for u, v, data in G.edges(data=True):
        clean_data = {}
        for k, val in data.items():
            if val is None:
                continue
            if isinstance(val, (str, int, float, bool)):
                clean_data[k] = val
            elif isinstance(val, list):
                clean_data[k] = json.dumps(val)
            else:
                clean_data[k] = str(val)
        G_clean.add_edge(u, v, **clean_data)

    return G_clean
