"use client";

import type { CSSProperties, ReactNode, ButtonHTMLAttributes } from "react";

/* ══════════════════════════════════════════════════════════════════════
   Shared UI Primitives — NEO Design System
   ══════════════════════════════════════════════════════════════════════ */

/* ── Color Maps (hoisted outside component per rendering-hoist-jsx) ── */

const BADGE_COLORS: Record<string, { bg: string; c: string; b: string }> = {
  accent: { bg: "var(--Od)", c: "var(--O)", b: "var(--O)" },
  green: { bg: "var(--Gd)", c: "var(--G)", b: "var(--G)" },
  blue: { bg: "var(--Bd)", c: "var(--B)", b: "var(--B)" },
  red: { bg: "var(--Rd)", c: "var(--R)", b: "var(--R)" },
  amber: { bg: "var(--Ad)", c: "var(--A)", b: "var(--A)" },
  purple: { bg: "rgba(139,92,246,.1)", c: "#A78BFA", b: "#A78BFA" },
  teal: { bg: "rgba(6,182,212,.1)", c: "#22D3EE", b: "#22D3EE" },
  ghost: { bg: "var(--c2)", c: "var(--t2)", b: "var(--bd)" },
};

const BTN_VARIANTS: Record<string, CSSProperties> = {
  primary: { background: "var(--t1)", color: "var(--bg)", borderColor: "var(--t1)" },
  secondary: { background: "var(--c2)", color: "var(--t1)", borderColor: "var(--bd)" },
  ghost: { background: "transparent", color: "var(--t2)" },
  accent: { background: "var(--O)", color: "#fff", borderColor: "var(--O)" },
};

/* ── Badge ── */

type BadgeProps = {
  children: ReactNode;
  color?: string;
  style?: CSSProperties;
};

export function Badge({ children, color = "accent", style }: BadgeProps) {
  const C = BADGE_COLORS[color] || BADGE_COLORS.accent;
  return (
    <span
      className="mono"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 6px",
        borderRadius: 2,
        background: C.bg,
        color: C.c,
        border: `1px solid ${C.b}40`,
        fontSize: 9,
        fontWeight: 500,
        letterSpacing: "0.02em",
        ...style,
      }}
    >
      {children}
    </span>
  );
}

/* ── Card ── */

type CardProps = {
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
};

export function Card({ children, style, className = "", ...rest }: CardProps) {
  return (
    <div
      style={{
        background: "var(--c1)",
        border: "1px solid var(--bd)",
        borderRadius: "var(--rd)",
        padding: 16,
        ...style,
      }}
      className={className}
      {...rest}
    >
      {children}
    </div>
  );
}

/* ── Btn ── */

type BtnProps = {
  children: ReactNode;
  v?: "primary" | "secondary" | "ghost" | "accent";
  sm?: boolean;
  icon?: ReactNode;
  style?: CSSProperties;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export function Btn({
  children,
  v = "primary",
  sm,
  icon,
  disabled,
  style,
  ...rest
}: BtnProps) {
  const vs = BTN_VARIANTS[v] || BTN_VARIANTS.primary;
  return (
    <button
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontFamily: "var(--font-mono), monospace",
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        border: "1px solid transparent",
        borderRadius: "var(--rs)",
        transition: "filter 0.15s",
        opacity: disabled ? 0.5 : 1,
        fontSize: sm ? 11 : 12,
        padding: sm ? "4px 10px" : "8px 16px",
        height: sm ? 28 : 36,
        ...vs,
        ...style,
      }}
      disabled={disabled}
      {...rest}
    >
      {icon ? <span style={{ fontSize: 14 }}>{icon}</span> : null}
      {children}
    </button>
  );
}

/* ── Spin ── */

type SpinProps = { sz?: number };

export function Spin({ sz = 12 }: SpinProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      style={{
        width: sz,
        height: sz,
        border: "2px solid var(--bd)",
        borderTopColor: "var(--O)",
        borderRadius: "50%",
        animation: "spin 0.7s linear infinite",
        display: "inline-block",
      }}
    />
  );
}
