"use client";

import { CAP } from "../lib/capabilities";

type CapPillProps = {
  field: string;
  value: boolean | number | null | undefined;
  confidence?: number;
  onClick?: () => void;
};

export default function CapPill({ field, value, confidence, onClick }: CapPillProps) {
  const m = CAP[field] || { l: field, i: "•", g: "Other" };
  if (value === null || value === undefined) return null;

  const isTrue = value === true;
  const isFalse = value === false;
  const isNum = typeof value === "number";
  const conf = confidence || 0;

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`${m.l}: ${isTrue ? "available" : isFalse ? "unavailable" : value}`}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 7,
        padding: "5px 10px",
        borderRadius: "var(--rs)",
        background: isFalse ? "var(--Rd)" : "var(--c2)",
        border: `1px solid ${isFalse ? "rgba(239,68,68,.12)" : "var(--bd)"}`,
        cursor: onClick ? "pointer" : "default",
        fontSize: 11,
        transition: "border-color 0.1s",
        color: "var(--t1)",
        fontFamily: "inherit",
        textAlign: "left",
        width: "100%",
      }}
    >
      <span style={{ fontSize: 12 }}>{m.i}</span>
      <span style={{ flex: 1, fontWeight: 500 }}>{m.l}</span>
      <span className="mono" style={{ fontSize: 10, fontWeight: 600 }}>
        {isTrue ? "✓" : isFalse ? "✗" : isNum ? value : String(value)}
      </span>
      {conf > 0 ? (
        <span
          className="mono"
          style={{
            fontSize: 8,
            padding: "1px 4px",
            borderRadius: 6,
            background: conf >= 0.8 ? "var(--Gd)" : conf >= 0.5 ? "var(--Ad)" : "var(--Rd)",
            color: conf >= 0.8 ? "var(--G)" : conf >= 0.5 ? "var(--A)" : "var(--R)",
          }}
        >
          {(conf * 100).toFixed(0)}%
        </span>
      ) : null}
    </button>
  );
}
