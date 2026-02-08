"use client";

import { useState, useCallback } from "react";
import type { Facility } from "../lib/types";
import { parseCSV } from "../lib/csv";
import { ragIndex } from "../lib/rag";
import Header from "../components/Header";
import OverviewScreen from "../components/OverviewScreen";
import MissionScreen from "../components/MissionScreen";
import GraphScreen from "../components/GraphScreen";
import DetailScreen from "../components/DetailScreen";

type Screen = "overview" | "mission" | "graph" | "detail";

const TABS = [
  { id: "graph" as const, l: "GRAPH VIEW", i: "🕸️" },
  { id: "overview" as const, l: "OVERVIEW & DESERTS", i: "🗺️" },
  { id: "mission" as const, l: "MISSION PLANNER", i: "📡" },
] as const;

export default function Home() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [screen, setScreen] = useState<Screen>("overview");
  const [selFac, setSelFac] = useState<Facility | null>(null);

  // Stats (derived during render — rerender-derived-state-no-effect)
  const extracted = facilities.filter(
    (x) => Object.keys(x.capabilities).length > 0
  ).length;
  const geocoded = facilities.filter((x) => x.lat != null).length;
  const totalAnomalies = facilities.reduce(
    (s, x) => s + (x.anomalies || []).length,
    0
  );
  // Simple desert approximation for header
  const desertCount = 0; // Will be computed accurately by OverviewScreen

  const handleUpload = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result;
      if (typeof text !== "string") return;
      const parsed = parseCSV(text);
      ragIndex.build(parsed);
      setFacilities(parsed);
      setScreen("overview");
    };
    reader.readAsText(file);
  }, []);

  const handleFacClick = useCallback((fac: Facility) => {
    setSelFac(fac);
    setScreen("detail");
  }, []);

  const handleFacUpdate = useCallback((updated: Facility) => {
    setFacilities((prev) =>
      prev.map((f) => (f.id === updated.id ? updated : f))
    );
  }, []);

  const hasData = facilities.length > 0;

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Header
        facilityCount={facilities.length}
        extracted={extracted}
        geocoded={geocoded}
        deserts={desertCount}
        anomalies={totalAnomalies}
        onUpload={handleUpload}
      />

      <main
        style={{
          marginTop: 60,
          flex: 1,
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Empty State */}
        {!hasData ? (
          <div
            style={{
              width: "100%",
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background:
                "radial-gradient(circle at center, #111 0%, #050505 70%)",
            }}
          >
            <div style={{ textAlign: "center", opacity: 0.5 }}>
              <div style={{ fontSize: 40, marginBottom: 10 }}>🌍</div>
              <div
                style={{
                  fontSize: 14,
                  color: "var(--t2)",
                  letterSpacing: "0.05em",
                }}
              >
                WAITING FOR DATA UPLOAD
              </div>
              <p
                style={{
                  fontSize: 11,
                  color: "var(--t3)",
                  marginTop: 5,
                }}
              >
                Click &ldquo;Upload CSV&rdquo; to initialize interface
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Tab Navigation */}
            <nav
              style={{
                height: 40,
                borderBottom: "1px solid var(--bd)",
                display: "flex",
                alignItems: "center",
                padding: "0 20px",
                gap: 20,
              }}
              aria-label="Screen navigation"
            >
              {TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setScreen(t.id)}
                  aria-current={screen === t.id ? "page" : undefined}
                  style={{
                    background: "none",
                    border: "none",
                    borderBottom:
                      screen === t.id
                        ? "2px solid var(--B)"
                        : "2px solid transparent",
                    color:
                      screen === t.id ? "var(--t1)" : "var(--t3)",
                    fontSize: 11,
                    fontWeight: 700,
                    padding: "10px 0",
                    cursor: "pointer",
                    display: "flex",
                    gap: 6,
                    letterSpacing: "0.05em",
                    fontFamily: "inherit",
                  }}
                >
                  <span
                    style={{ opacity: screen === t.id ? 1 : 0.5 }}
                  >
                    {t.i}
                  </span>{" "}
                  {t.l}
                </button>
              ))}
            </nav>

            {/* Screen Content */}
            <div
              style={{
                height: "calc(100% - 40px)",
                position: "relative",
              }}
            >
              {screen === "overview" ? (
                <OverviewScreen
                  facilities={facilities}
                  onFacClick={handleFacClick}
                />
              ) : null}
              {screen === "mission" ? (
                <MissionScreen
                  facilities={facilities}
                  onFacClick={handleFacClick}
                />
              ) : null}
              {screen === "graph" ? (
                <GraphScreen
                  facilities={facilities}
                  onFacClick={handleFacClick}
                />
              ) : null}
              {screen === "detail" ? (
                <DetailScreen
                  fac={selFac}
                  onBack={() => setScreen("overview")}
                  onUpdate={handleFacUpdate}
                />
              ) : null}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
