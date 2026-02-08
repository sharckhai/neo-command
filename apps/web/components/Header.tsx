"use client";

import { useState, useRef, type ChangeEvent } from "react";
import { Btn } from "./ui";

type HeaderProps = {
  facilityCount: number;
  extracted: number;
  geocoded: number;
  deserts: number;
  anomalies: number;
  onUpload: (file: File) => void;
};

type StatItem = {
  l: string;
  key: "facilityCount" | "extracted" | "geocoded" | "deserts" | "anomalies";
  warnKey?: boolean;
};

const STAT_ITEMS: StatItem[] = [
  { l: "FACILITIES", key: "facilityCount" },
  { l: "EXTRACTED", key: "extracted" },
  { l: "GEOCODED", key: "geocoded" },
  { l: "DESERTS", key: "deserts", warnKey: true },
  { l: "ANOMALIES", key: "anomalies", warnKey: true },
];

export default function Header({
  facilityCount,
  extracted,
  geocoded,
  deserts,
  anomalies,
  onUpload,
}: HeaderProps) {
  const [showSettings, setShowSettings] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const stats: Record<string, number> = {
    facilityCount,
    extracted,
    geocoded,
    deserts,
    anomalies,
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <header
      style={{
        height: 60,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: "rgba(5,5,5,0.85)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--bd)",
      }}
    >
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 8,
              height: 8,
              background: "var(--t1)",
              borderRadius: "50%",
            }}
          />
          <span
            style={{
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: "0.05em",
            }}
          >
            NEO
          </span>
        </div>
        <div
          className="mono"
          style={{
            fontSize: 10,
            color: "var(--t3)",
            borderLeft: "1px solid var(--bd)",
            paddingLeft: 12,
            height: 20,
            display: "flex",
            alignItems: "center",
          }}
        >
          GHANA FACILITIES
        </div>
      </div>

      {/* Stats */}
      {facilityCount > 0 ? (
        <nav
          style={{ display: "flex", gap: 24 }}
          aria-label="Facility statistics"
        >
          {STAT_ITEMS.map((s) => {
            const val = stats[s.key];
            const isWarn = s.warnKey && val > 0;
            return (
              <div key={s.l} style={{ textAlign: "left" }}>
                <div
                  className="mono"
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: isWarn
                      ? s.key === "deserts"
                        ? "var(--R)"
                        : "var(--A)"
                      : "var(--t1)",
                    lineHeight: 1,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {val}
                </div>
                <div
                  style={{
                    fontSize: 9,
                    color: "var(--t3)",
                    fontWeight: 600,
                    letterSpacing: "0.05em",
                    marginTop: 3,
                  }}
                >
                  {s.l}
                </div>
              </div>
            );
          })}
        </nav>
      ) : null}

      {/* Actions */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", position: "relative" }}>
        <button
          onClick={() => setShowSettings(!showSettings)}
          aria-label={showSettings ? "Close Settings" : "Open Settings"}
          style={{
            background: "none",
            border: "none",
            color: "var(--t2)",
            cursor: "pointer",
            fontSize: 18,
          }}
        >
          {showSettings ? "✕" : "⚙"}
        </button>

        {showSettings ? (
          <div
            style={{
              position: "absolute",
              top: 50,
              right: 0,
              width: 320,
              background: "var(--c1)",
              border: "1px solid var(--bd)",
              borderRadius: 6,
              padding: 16,
              boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
              zIndex: 2000,
            }}
          >
            <h3
              style={{
                fontSize: 12,
                fontWeight: 700,
                marginBottom: 12,
                textTransform: "uppercase",
                color: "var(--t2)",
              }}
            >
              System Configuration
            </h3>
            <p style={{ fontSize: 11, color: "var(--t3)", lineHeight: 1.5 }}>
              This app uses the backend /api/chat endpoint for AI queries.
              Configure any additional settings here.
            </p>
          </div>
        ) : null}

        <Btn
          sm
          v="secondary"
          icon="📤"
          onClick={() => fileRef.current?.click()}
          aria-label="Upload CSV File"
        >
          Upload CSV
        </Btn>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={handleFileChange}
          aria-label="CSV file input"
        />
      </div>
    </header>
  );
}
