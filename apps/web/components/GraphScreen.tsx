"use client";

import { useEffect, useRef, useState } from "react";
import type { Facility } from "../lib/types";
import { Badge } from "./ui";

type GraphScreenProps = {
  facilities: Facility[];
  onFacClick: (fac: Facility) => void;
};

export default function GraphScreen({
  facilities,
  onFacClick,
}: GraphScreenProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });

  useEffect(() => {
    if (!facilities.length || !svgRef.current) return;

    let simulation: any = null;

    // Dynamic import for D3 (bundle-dynamic-imports)
    import("d3").then((d3) => {
      if (!svgRef.current) return;

      // 1. Prepare Nodes
      const activeNodes = facilities
        .map((f) => {
          const caps = Object.keys(f.capabilities || {}).filter(
            (k) => f.capabilities[k] === true
          );
          return {
            ...f,
            score: caps.length,
            caps,
            x: Math.random() * 800,
            y: Math.random() * 600,
            phase: Math.random() * Math.PI * 2,
            speed: 0.0005 + Math.random() * 0.001,
          };
        })
        .filter((n) => n.score > 0);

      // 2. Prepare Edges (Jaccard similarity > 0.3)
      const links: { source: string; target: string; value: number }[] = [];
      for (let i = 0; i < activeNodes.length; i++) {
        const source = activeNodes[i];
        if (source.caps.length === 0) continue;
        const candidates: { id: string; sim: number }[] = [];
        for (let j = i + 1; j < activeNodes.length; j++) {
          const target = activeNodes[j];
          const intersection = source.caps.filter((c) =>
            target.caps.includes(c)
          ).length;
          const union = new Set([...source.caps, ...target.caps]).size;
          const sim = union === 0 ? 0 : intersection / union;
          if (sim > 0.3) candidates.push({ id: target.id, sim });
        }
        candidates
          .sort((a, b) => b.sim - a.sim)
          .slice(0, 3)
          .forEach((c) => {
            links.push({ source: source.id, target: c.id, value: c.sim });
          });
      }

      setStats({ nodes: activeNodes.length, edges: links.length });

      // 3. D3 Setup
      const width = window.innerWidth;
      const height = window.innerHeight - 100;
      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();

      const g = svg.append("g");

      // Zoom
      const zoom = d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 8])
        .on("zoom", (e) => g.attr("transform", e.transform));
      svg.call(zoom);
      svg.call(
        zoom.transform,
        d3.zoomIdentity.translate(width / 2, height / 2).scale(0.5)
      );

      simulation = d3
        .forceSimulation(activeNodes as any)
        .force(
          "link",
          d3
            .forceLink(links)
            .id((d: any) => d.id)
            .distance(100)
        )
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(0, 0))
        .force(
          "collide",
          d3.forceCollide((d: any) => 8 + d.score * 0.8)
        )
        .alphaTarget(0.005);

      const link = g
        .append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.3)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", (d) => Math.sqrt(d.value) * 3);

      // Drag handler
      function drag(sim: any) {
        return d3
          .drag<SVGGElement, any>()
          .on("start", (event) => {
            if (!event.active) sim.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
          })
          .on("drag", (event) => {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
          })
          .on("end", (event) => {
            if (!event.active) sim.alphaTarget(0.005);
            event.subject.fx = null;
            event.subject.fy = null;
          });
      }

      const node = g
        .append("g")
        .selectAll<SVGGElement, any>("g")
        .data(activeNodes)
        .join("g")
        .call(drag(simulation));

      // Node Circle
      node
        .append("circle")
        .attr("r", (d) => 6 + d.score * 1.5)
        .attr("fill", (d) =>
          d.score < 3 ? "#ef4444" : d.score < 8 ? "#f59e0b" : "#10b981"
        )
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .attr("stroke-opacity", 0.8);

      // Node Label (only for prominent nodes)
      node
        .filter((d) => d.score > 5)
        .append("text")
        .text((d) =>
          d.name.length > 15 ? d.name.slice(0, 15) + "…" : d.name
        )
        .attr("x", 12)
        .attr("y", 4)
        .attr("font-size", 10)
        .attr("fill", "#ccc")
        .style("pointer-events", "none");

      // Tooltip via title
      node
        .append("title")
        .text(
          (d) =>
            `${d.name}\n${d.city}\nCapabilities (${d.score}): ${d.caps.join(", ")}`
        );

      // Click handler
      node.on("click", (_e, d) => onFacClick(d as any));

      // Tick with gentle breathing animation
      simulation.on("tick", () => {
        const t = Date.now();
        link
          .attr(
            "x1",
            (d: any) =>
              d.source.x +
              Math.sin(t * d.source.speed + d.source.phase) * 2
          )
          .attr(
            "y1",
            (d: any) =>
              d.source.y +
              Math.cos(t * d.source.speed + d.source.phase) * 2
          )
          .attr(
            "x2",
            (d: any) =>
              d.target.x +
              Math.sin(t * d.target.speed + d.target.phase) * 2
          )
          .attr(
            "y2",
            (d: any) =>
              d.target.y +
              Math.cos(t * d.target.speed + d.target.phase) * 2
          );

        node.attr(
          "transform",
          (d: any) =>
            `translate(${d.x + Math.sin(t * d.speed + d.phase) * 2},${d.y + Math.cos(t * d.speed + d.phase) * 2})`
        );
      });
    });

    return () => {
      if (simulation) simulation.stop();
    };
  }, [facilities, onFacClick]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        overflow: "hidden",
        background: "#060a10",
        position: "relative",
      }}
    >
      {/* Legend overlay */}
      <div
        style={{
          position: "absolute",
          top: 20,
          left: 20,
          zIndex: 10,
          background: "rgba(6,10,16,0.9)",
          padding: 15,
          borderRadius: 8,
          border: "1px solid var(--bd)",
          boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
        }}
      >
        <h2
          style={{ fontSize: 16, fontWeight: 700, marginBottom: 5 }}
        >
          GraphRAG Visualization
        </h2>
        <p
          style={{
            fontSize: 12,
            color: "var(--t2)",
            marginBottom: 10,
          }}
        >
          Nodes connected by service similarity (&gt;30% overlap)
        </p>
        <div
          style={{
            display: "flex",
            gap: 12,
            fontSize: 11,
            marginBottom: 8,
          }}
        >
          <div
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#ef4444",
              }}
            />
            Scarce (0-3)
          </div>
          <div
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#f59e0b",
              }}
            />
            Moderate (4-8)
          </div>
          <div
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#10b981",
              }}
            />
            Abundant (&gt;8)
          </div>
        </div>
        <div style={{ fontSize: 10, color: "var(--t3)" }}>
          Active Nodes: {stats.nodes} | Edges: {stats.edges}
        </div>
        <p style={{ fontSize: 10, color: "var(--t3)", marginTop: 4 }}>
          Drag nodes to rearrange. Scroll to zoom. Click for details.
        </p>
      </div>
      <svg
        ref={svgRef}
        style={{ width: "100%", height: "100%", cursor: "grab" }}
        role="img"
        aria-label={`Graph visualization with ${stats.nodes} facility nodes and ${stats.edges} similarity edges`}
      />
    </div>
  );
}
