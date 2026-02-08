"use client";

import type { AgentStep } from "../lib/capabilities";
import { Badge } from "./ui";
import { Spin } from "./ui";

type AgentTraceProps = {
  steps: AgentStep[];
};

export default function AgentTrace({ steps }: AgentTraceProps) {
  if (!steps || steps.length === 0) return null;

  return (
    <div style={{ position: "relative" }}>
      {steps.map((s, i) => (
        <div key={i} className={`agent-step ${s.status}`}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              marginBottom: 4,
            }}
          >
            <Badge
              color={
                s.status === "done"
                  ? "green"
                  : s.status === "running"
                    ? "accent"
                    : "red"
              }
              style={{ fontSize: 9 }}
            >
              {s.agent}
            </Badge>
            <span style={{ fontSize: 11, fontWeight: 600 }}>{s.action}</span>
            {s.status === "running" ? <Spin sz={10} /> : null}
          </div>
          <div style={{ fontSize: 10, color: "var(--t3)", marginBottom: 3 }}>
            <b>Input:</b>{" "}
            {typeof s.input === "string"
              ? s.input.slice(0, 120)
              : JSON.stringify(s.input).slice(0, 120)}
          </div>
          <div style={{ fontSize: 11, color: "var(--t2)", marginBottom: 4 }}>
            <b>Output:</b>{" "}
            {typeof s.output === "string"
              ? s.output.slice(0, 200)
              : JSON.stringify(s.output).slice(0, 200)}
          </div>
          {s.citations?.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              {s.citations.slice(0, 4).map((c, j) => (
                <div
                  key={j}
                  style={{
                    fontSize: 10,
                    padding: "3px 8px",
                    borderRadius: 4,
                    background: "var(--c3)",
                    borderLeft: `2px solid ${s.status === "done" ? "var(--G)" : "var(--O)"}`,
                    color: "var(--t2)",
                  }}
                >
                  <b style={{ color: "var(--t1)" }}>[{c.field}]</b>{" "}
                  {c.snippet?.slice(0, 140)}
                  {c.row ? (
                    <span className="mono" style={{ color: "var(--t3)" }}>
                      {" "}
                      (row {c.row})
                    </span>
                  ) : null}
                </div>
              ))}
              {s.citations.length > 4 ? (
                <span style={{ fontSize: 9, color: "var(--t3)" }}>
                  +{s.citations.length - 4} more citations
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
