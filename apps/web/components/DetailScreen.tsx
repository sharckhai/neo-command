"use client";

import { useState } from "react";
import type { Facility } from "../lib/types";
import { CAP } from "../lib/capabilities";
import { Badge, Card, Btn, Spin } from "./ui";
import CapPill from "./CapPill";
import AgentTrace from "./AgentTrace";

type DetailScreenProps = {
  fac: Facility | null;
  onBack: () => void;
  onUpdate: (updated: Facility) => void;
};

export default function DetailScreen({
  fac: f,
  onBack,
  onUpdate,
}: DetailScreenProps) {
  const [citField, setCitField] = useState<string | null>(null);
  const [showTrace, setShowTrace] = useState(true);

  if (!f) return null;

  const caps = f.capabilities || {};
  const conf = f.confidence || {};
  const cits = f.citations || [];
  const anoms = f.anomalies || [];

  // Group capabilities by category
  const groups: Record<string, { field: string; value: boolean | number; confidence: number }[]> =
    {};
  for (const [k, v] of Object.entries(caps)) {
    if (v === null || v === undefined) continue;
    const m = CAP[k] || { g: "Other" };
    if (!groups[m.g]) groups[m.g] = [];
    groups[m.g].push({ field: k, value: v, confidence: conf[k] || 0 });
  }

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: "18px 20px" }}>
      <button
        onClick={onBack}
        style={{
          background: "none",
          border: "none",
          color: "var(--t3)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 4,
          fontSize: 11,
          fontWeight: 500,
          marginBottom: 12,
          fontFamily: "inherit",
        }}
        aria-label="Back to analysis"
      >
        ← Back to Analysis
      </button>

      {/* Facility Header */}
      <div className="fu" style={{ marginBottom: 18 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: 10,
          }}
        >
          <div>
            <h1
              style={{
                fontSize: 20,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                marginBottom: 5,
              }}
            >
              {f.name}
            </h1>
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              {f.city ? <Badge color="accent">{f.city}</Badge> : null}
              {f.region ? <Badge color="blue">{f.region}</Badge> : null}
              {f.facility_type ? (
                <Badge color="ghost">{f.facility_type}</Badge>
              ) : null}
              {f.operator_type ? (
                <Badge color="purple">{f.operator_type}</Badge>
              ) : null}
              {f.aiExtracted ? <Badge color="green">AI Enhanced</Badge> : null}
              {anoms.length > 0 ? (
                <Badge color="red">⚠ {anoms.length}</Badge>
              ) : null}
              {f._rows ? (
                <Badge color="teal" style={{ fontSize: 9 }}>
                  Row{f._rows.length > 1 ? "s" : ""} {f._rows.join(",")}
                </Badge>
              ) : null}
            </div>
            {f.description ? (
              <p
                style={{
                  marginTop: 6,
                  fontSize: 11,
                  color: "var(--t2)",
                  lineHeight: 1.6,
                  maxWidth: 560,
                }}
              >
                {f.description.length > 250
                  ? f.description.slice(0, 250) + "…"
                  : f.description}
              </p>
            ) : null}
            <div
              style={{
                marginTop: 4,
                display: "flex",
                gap: 8,
                fontSize: 10,
                color: "var(--t3)",
                flexWrap: "wrap",
              }}
            >
              {f.phone ? <span>📞 {f.phone}</span> : null}
              {f.email ? <span>✉ {f.email}</span> : null}
              {f.website ? <span>🌐 {f.website}</span> : null}
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <Btn
              sm
              v="secondary"
              onClick={() => setShowTrace(!showTrace)}
            >
              {showTrace ? "Hide" : "Show"} Pipeline
            </Btn>
          </div>
        </div>
      </div>

      {/* Content Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: showTrace ? "1fr 360px" : "1fr",
          gap: 14,
          alignItems: "start",
        }}
      >
        <div>
          {/* Anomalies */}
          {anoms.length > 0 ? (
            <Card
              className="fu d1"
              style={{
                marginBottom: 12,
                borderColor: "rgba(239,68,68,.15)",
              }}
            >
              <div
                style={{
                  fontWeight: 600,
                  fontSize: 12,
                  color: "var(--R)",
                  marginBottom: 6,
                }}
              >
                ⚠ Anomalies ({anoms.length})
              </div>
              {anoms.map((a, i) => (
                <div
                  key={i}
                  style={{
                    padding: "5px 9px",
                    marginBottom: 3,
                    borderRadius: "var(--rs)",
                    background:
                      a.severity === "error" ? "var(--Rd)" : "var(--Ad)",
                    fontSize: 10,
                  }}
                >
                  <b
                    style={{
                      color:
                        a.severity === "error" ? "var(--R)" : "var(--A)",
                    }}
                  >
                    {a.field}
                  </b>{" "}
                  <span style={{ color: "var(--t2)" }}>{a.message}</span>
                </div>
              ))}
            </Card>
          ) : null}

          {/* Capability Groups */}
          {Object.entries(groups).map(([g, items], gi) => (
            <Card
              key={g}
              className={`fu d${Math.min(gi + 1, 3)}`}
              style={{ marginBottom: 10 }}
            >
              <div
                style={{
                  fontWeight: 600,
                  fontSize: 10,
                  color: "var(--t3)",
                  textTransform: "uppercase",
                  letterSpacing: ".05em",
                  marginBottom: 7,
                }}
              >
                {g}
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fill,minmax(180px,1fr))",
                  gap: 4,
                }}
              >
                {items.map((it) => (
                  <CapPill
                    key={it.field}
                    {...it}
                    onClick={() => setCitField(it.field)}
                  />
                ))}
              </div>
            </Card>
          ))}

          {/* Specialties */}
          {f.specialties_list?.length > 0 ? (
            <Card className="fu d2" style={{ marginBottom: 10 }}>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: 10,
                  color: "var(--t3)",
                  textTransform: "uppercase",
                  letterSpacing: ".05em",
                  marginBottom: 6,
                }}
              >
                Specialties ({f.specialties_list.length})
              </div>
              <div
                style={{ display: "flex", flexWrap: "wrap", gap: 3 }}
              >
                {f.specialties_list.map((s, i) => (
                  <Badge key={i} color="accent" style={{ fontSize: 9 }}>
                    {s}
                  </Badge>
                ))}
              </div>
            </Card>
          ) : null}

          {/* Equipment */}
          {f.equipment_list?.length > 0 ? (
            <Card style={{ marginBottom: 10 }}>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: 10,
                  color: "var(--t3)",
                  textTransform: "uppercase",
                  letterSpacing: ".05em",
                  marginBottom: 6,
                }}
              >
                Equipment ({f.equipment_list.length})
              </div>
              <div
                style={{ display: "flex", flexWrap: "wrap", gap: 3 }}
              >
                {f.equipment_list.map((s, i) => (
                  <Badge key={i} color="blue" style={{ fontSize: 9 }}>
                    {s}
                  </Badge>
                ))}
              </div>
            </Card>
          ) : null}

          {/* Procedures */}
          {f.procedures_list?.length > 0 ? (
            <Card style={{ marginBottom: 10 }}>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: 10,
                  color: "var(--t3)",
                  textTransform: "uppercase",
                  letterSpacing: ".05em",
                  marginBottom: 6,
                }}
              >
                Procedures ({f.procedures_list.length})
              </div>
              <div
                style={{ display: "flex", flexWrap: "wrap", gap: 3 }}
              >
                {f.procedures_list.map((s, i) => (
                  <Badge key={i} color="green" style={{ fontSize: 9 }}>
                    {s}
                  </Badge>
                ))}
              </div>
            </Card>
          ) : null}
        </div>

        {/* Sidebar: IDP Pipeline Trace + Citations */}
        {showTrace ? (
          <div style={{ position: "sticky", top: 56 }}>
            <Card>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                IDP Extraction Pipeline
              </div>
              <p
                style={{
                  fontSize: 10,
                  color: "var(--t3)",
                  marginBottom: 10,
                }}
              >
                5-step extraction with row-level citations
              </p>
              <AgentTrace steps={f.steps || []} />
            </Card>

            {/* Citation panel for selected capability */}
            {citField ? (
              <Card style={{ marginTop: 10 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: 8,
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 12 }}>
                    Citations: <Badge color="accent">{citField}</Badge>
                  </div>
                  <button
                    onClick={() => setCitField(null)}
                    aria-label="Close citations"
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--t3)",
                      cursor: "pointer",
                      fontSize: 10,
                      fontFamily: "inherit",
                    }}
                  >
                    ✕
                  </button>
                </div>
                {cits
                  .filter((c) => c.field === citField)
                  .map((c, i) => (
                    <div
                      key={i}
                      style={{
                        fontSize: 10,
                        padding: "4px 8px",
                        marginBottom: 4,
                        borderRadius: 4,
                        background: "var(--c3)",
                        borderLeft: "2px solid var(--O)",
                        color: "var(--t2)",
                      }}
                    >
                      &ldquo;{c.snippet}&rdquo;{" "}
                      {c.row ? (
                        <span className="mono" style={{ color: "var(--t3)" }}>
                          row {c.row}
                        </span>
                      ) : null}
                    </div>
                  ))}
                {cits.filter((c) => c.field === citField).length === 0 ? (
                  <div style={{ fontSize: 10, color: "var(--t3)" }}>
                    No citations found for this capability.
                  </div>
                ) : null}
              </Card>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
