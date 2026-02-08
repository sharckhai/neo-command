"use client";

import { useState, useMemo, type ChangeEvent } from "react";
import type { Facility } from "../lib/types";
import { CAP } from "../lib/capabilities";
import MapPanel from "./MapPanel";
import { Badge, Card } from "./ui";

type OverviewScreenProps = {
  facilities: Facility[];
  onFacClick: (fac: Facility) => void;
};

const ADMIN_REGIONS: Record<string, string> = {
  "greater accra": "Greater Accra",
  ashanti: "Ashanti",
  western: "Western",
  central: "Central",
  eastern: "Eastern",
  volta: "Volta",
  northern: "Northern",
  "upper east": "Upper East",
  "upper west": "Upper West",
  "brong ahafo": "Brong Ahafo",
  "bono east": "Bono East",
  ahafo: "Ahafo",
  bono: "Bono",
  oti: "Oti",
  "western north": "Western North",
  "north east": "North East",
  savannah: "Savannah",
};

function toAdminRegion(f: Facility): string {
  const r = (f.region || "").toLowerCase().replace(" region", "").trim();
  if (ADMIN_REGIONS[r]) return ADMIN_REGIONS[r];
  if (f.lat) {
    if (f.lat > 10) return f.lng! < -1.5 ? "Upper West" : "Upper East";
    if (f.lat > 9) return f.lng! < -1 ? "Northern" : "North East";
    if (f.lat > 8) return f.lng! > 0 ? "Oti" : "Savannah";
    if (f.lat > 7) return f.lng! < -2 ? "Bono" : "Brong Ahafo";
    if (f.lat > 6.3)
      return f.lng! < -2
        ? "Ahafo"
        : f.lng! < -1
          ? "Ashanti"
          : f.lng! > 0
            ? "Volta"
            : "Eastern";
    if (f.lat > 5.5)
      return f.lng! < -1.5
        ? "Western"
        : f.lng! < -0.5
          ? "Central"
          : f.lng! < 0.2
            ? "Greater Accra"
            : "Volta";
    return f.lng! < -1.5 ? "Western" : "Central";
  }
  return "Unknown";
}

// Build capability dropdown options (hoisted, no render dep)
const capOpts = Object.entries(CAP)
  .filter(([, m]) => !m.n)
  .map(([k, m]) => ({ v: k, l: `${m.i} ${m.l}` }));

export default function OverviewScreen({
  facilities,
  onFacClick,
}: OverviewScreenProps) {
  const [selCap, setSelCap] = useState("emergency_24_7");
  const [filter, setFilter] = useState("");

  // Derive deserts during render (rerender-derived-state-no-effect)
  const deserts = useMemo(() => {
    const regs: Record<string, Facility[]> = {};
    for (const f of facilities) {
      const r = toAdminRegion(f);
      if (!regs[r]) regs[r] = [];
      regs[r].push(f);
    }
    return Object.entries(regs)
      .filter(
        ([r, fs]) =>
          r !== "Unknown" &&
          !fs.some(
            (f) => (f.capabilities || {})[selCap] === true
          )
      )
      .map(([region]) => ({
        region,
        capability: selCap,
        gap: `No ${(CAP[selCap] || {}).l || selCap} in ${region}`,
      }));
  }, [selCap, facilities]);

  // Derive filtered facilities during render
  const filteredFacilities = useMemo(() => {
    if (!filter) return facilities;
    const s = filter.toLowerCase();
    return facilities.filter(
      (f) =>
        (f.name || "").toLowerCase().includes(s) ||
        (f.city || "").toLowerCase().includes(s) ||
        (f.region || "").toLowerCase().includes(s)
    );
  }, [filter, facilities]);

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        position: "relative",
      }}
    >
      {/* Map takes full available space */}
      <div style={{ flex: 1, position: "relative" }}>
        <MapPanel
          facilities={filteredFacilities}
          selCap={selCap}
          onFacClick={onFacClick}
          desertRegions={deserts}
        />

        {/* Glassmorphism Control Panel Overlay */}
        <div
          style={{
            position: "absolute",
            bottom: 20,
            left: 20,
            width: 360,
            maxHeight: "60%",
            display: "flex",
            flexDirection: "column",
            gap: 10,
            zIndex: 500,
          }}
        >
          {/* Regional Health Status */}
          <Card
            className="fu"
            style={{
              padding: 0,
              overflow: "hidden",
              backdropFilter: "blur(20px)",
              background: "rgba(10,10,10,0.85)",
            }}
          >
            <div
              style={{
                height: 40,
                borderBottom: "1px solid var(--bd)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 12px",
                background: "var(--c1)",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.05em",
                  color: "var(--t2)",
                }}
              >
                REGIONAL HEALTH STATUS
              </div>
              <Badge color="blue">{deserts.length} REGIONS</Badge>
            </div>
            <div style={{ padding: 12 }}>
              <div style={{ marginBottom: 12 }}>
                <label htmlFor="cap-select" className="sr-only" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0,0,0,0)" }}>
                  Select capability to check
                </label>
                <select
                  id="cap-select"
                  value={selCap}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                    setSelCap(e.target.value)
                  }
                  style={{
                    width: "100%",
                    padding: "6px 10px",
                    borderRadius: "var(--rs)",
                    background: "var(--c2)",
                    border: "1px solid var(--bd)",
                    color: "var(--t1)",
                    fontSize: 11,
                    outline: "none",
                  }}
                >
                  {capOpts.map((o) => (
                    <option key={o.v} value={o.v}>
                      {o.l}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ maxHeight: 200, overflowY: "auto" }}>
                {deserts.length === 0 ? (
                  <div
                    style={{
                      padding: 10,
                      textAlign: "center",
                      color: "var(--t3)",
                      fontSize: 11,
                    }}
                  >
                    No coverage gaps detected
                  </div>
                ) : (
                  deserts.map((d, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 0",
                        borderBottom: "1px solid var(--bd)",
                      }}
                    >
                      <div
                        style={{
                          width: 4,
                          height: 4,
                          background: "var(--R)",
                          borderRadius: "50%",
                          boxShadow: "0 0 5px var(--R)",
                          flexShrink: 0,
                        }}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: 12 }}>
                          {d.region}
                        </div>
                        <div style={{ fontSize: 10, color: "var(--R)" }}>
                          CRITICAL GAP: {d.capability.toUpperCase()}
                        </div>
                      </div>
                      <Badge color="red">HIGH</Badge>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>

          {/* Quick Facility Search */}
          <Card
            className="fu"
            style={{
              padding: 12,
              backdropFilter: "blur(20px)",
              background: "rgba(10,10,10,0.85)",
            }}
          >
            <label htmlFor="fac-filter" className="sr-only" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0,0,0,0)" }}>
              Filter facilities
            </label>
            <input
              id="fac-filter"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter facilities…"
              style={{
                width: "100%",
                padding: "6px 10px",
                borderRadius: "var(--rs)",
                background: "var(--c2)",
                border: "1px solid var(--bd)",
                color: "var(--t1)",
                fontSize: 11,
                outline: "none",
              }}
            />
            {filter ? (
              <div
                style={{ fontSize: 10, color: "var(--t3)", marginTop: 4 }}
              >
                Found {filteredFacilities.length} matches
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
