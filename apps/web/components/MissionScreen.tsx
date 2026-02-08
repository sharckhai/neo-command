"use client";

import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { parseEventStream } from "../lib/sse";
import type { ChatResponse, TraceEvent, Facility } from "../lib/types";
import { Card, Btn, Badge, Spin } from "./ui";
import AgentTrace from "./AgentTrace";
import type { AgentStep } from "../lib/capabilities";

type TraceStep = {
  name: string;
  args: string;
  output?: string;
  status: "running" | "done" | "error";
};

type Message = {
  role: "user" | "assistant";
  content: string;
  mode?: string;
  trace?: TraceStep[];
};

type MissionScreenProps = {
  facilities: Facility[];
  onFacClick: (fac: Facility) => void;
};

const STARTER_PROMPTS = [
  {
    label: "Explore",
    prompt: "How many facilities offer cardiology?",
    color: "accent" as const,
  },
  {
    label: "Verify",
    prompt: "Which facilities have suspicious capability claims?",
    color: "green" as const,
  },
  {
    label: "Plan",
    prompt:
      "I have 2 ophthalmologists for 10 days. Where should I send them?",
    color: "blue" as const,
  },
];

const MODE_BADGE_COLORS: Record<string, string> = {
  EXPLORE: "accent",
  VERIFY: "green",
  PLAN: "blue",
};

export default function MissionScreen({
  facilities,
  onFacClick,
}: MissionScreenProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const chatBodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (overridePrompt?: string) => {
    const prompt = (overridePrompt ?? input).trim();
    if (!prompt || isLoading) return;
    setInput("");
    setIsLoading(true);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: prompt },
      { role: "assistant", content: "" },
    ]);

    let traceSteps: TraceStep[] = [];

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: prompt, session_id: "local" }),
      });
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalPayload: ChatResponse | null = null;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const events = parseEventStream(part + "\n\n");
          for (const event of events) {
            if (event.type === "token") {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                updated[updated.length - 1] = {
                  ...last,
                  content: (last.content || "") + event.text,
                  trace: traceSteps.length ? [...traceSteps] : last.trace,
                };
                return updated;
              });
            }
            if (event.type === "trace") {
              traceSteps = [
                ...traceSteps,
                {
                  name: event.step.name,
                  args: event.step.args,
                  status: "running",
                },
              ];
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                updated[updated.length - 1] = {
                  ...last,
                  trace: [...traceSteps],
                };
                return updated;
              });
            }
            if (event.type === "final") {
              finalPayload = event.payload;
              const completedTrace: TraceStep[] = (
                event.payload.trace ?? []
              ).map((t: TraceEvent) => ({
                name: t.name,
                args: JSON.stringify(t.input).slice(0, 120),
                output: JSON.stringify(t.output).slice(0, 200),
                status: "done" as const,
              }));
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: event.payload.answer,
                  mode: event.payload.mode,
                  trace: completedTrace.length
                    ? completedTrace
                    : traceSteps.map((s) => ({
                        ...s,
                        status: "done" as const,
                      })),
                };
                return updated;
              });
            }
          }
        }
      }

      if (finalPayload) {
        window.dispatchEvent(
          new CustomEvent("map-actions", { detail: finalPayload })
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const showStarters = messages.length === 0 && !isLoading;

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "450px 1fr",
        gap: 20,
        padding: 20,
        height: "100%",
      }}
    >
      {/* Left Panel: Chat Interface */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <Card
          className="fu"
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            padding: 20,
          }}
        >
          <div style={{ marginBottom: 20 }}>
            <h2
              style={{
                fontSize: 20,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                marginBottom: 8,
              }}
            >
              NEO Mission Control
            </h2>
            <p
              style={{
                fontSize: 12,
                color: "var(--t2)",
                lineHeight: 1.5,
              }}
            >
              Analyze facility data, cross-reference with national policy, and
              detect operational gaps. Ask anything.
            </p>
          </div>

          {/* Chat messages */}
          <div
            ref={chatBodyRef}
            style={{
              flex: 1,
              overflowY: "auto",
              marginBottom: 14,
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  padding: "10px 12px",
                  borderRadius: "var(--rs)",
                  background:
                    msg.role === "user" ? "var(--c2)" : "var(--c1)",
                  border: "1px solid var(--bd)",
                  fontSize: 12,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    marginBottom: 4,
                  }}
                >
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: "0.05em",
                      textTransform: "uppercase",
                      color: "var(--t3)",
                    }}
                  >
                    {msg.role === "user" ? "Planner" : "NEO"}
                  </span>
                  {msg.mode ? (
                    <Badge color={MODE_BADGE_COLORS[msg.mode] || "ghost"}>
                      {msg.mode}
                    </Badge>
                  ) : null}
                </div>
                <div style={{ lineHeight: 1.6, color: "var(--t1)" }}>
                  {msg.content}
                </div>
                {msg.trace && msg.trace.length > 0 ? (
                  <MiniTrace steps={msg.trace} />
                ) : null}
              </div>
            ))}
            {isLoading &&
            messages.length > 0 &&
            messages[messages.length - 1]?.content === "" ? (
              <div
                style={{
                  textAlign: "center",
                  padding: 12,
                  fontSize: 12,
                  color: "var(--t3)",
                }}
              >
                <Spin sz={14} /> Analyzing…
              </div>
            ) : null}
          </div>

          {/* Starter Prompts */}
          {showStarters ? (
            <div
              style={{
                display: "grid",
                gap: 8,
                marginBottom: 14,
              }}
            >
              {STARTER_PROMPTS.map((sp) => (
                <button
                  key={sp.label}
                  onClick={() => handleSubmit(sp.prompt)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    textAlign: "left",
                    background: "var(--c2)",
                    border: "1px solid var(--bd)",
                    borderRadius: "var(--rs)",
                    padding: "10px 12px",
                    cursor: "pointer",
                    color: "var(--t1)",
                    fontFamily: "inherit",
                    fontSize: 12,
                    transition: "border-color 0.15s",
                  }}
                >
                  <Badge color={sp.color}>{sp.label}</Badge>
                  <span>{sp.prompt}</span>
                </button>
              ))}
            </div>
          ) : null}

          {/* Input */}
          <div style={{ position: "relative" }}>
            <label htmlFor="mission-input" className="sr-only" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0,0,0,0)" }}>
              Mission objective
            </label>
            <textarea
              id="mission-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your objective…"
              className="mono"
              rows={3}
              onKeyDown={handleKeyDown}
              style={{
                width: "100%",
                padding: 16,
                borderRadius: "var(--rs)",
                background: "var(--c2)",
                border: "1px solid var(--bd)",
                color: "var(--t1)",
                fontSize: 12,
                outline: "none",
                resize: "none",
              }}
            />
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: 10,
            }}
          >
            <Btn
              onClick={() => handleSubmit()}
              disabled={!input.trim() || isLoading}
              icon={isLoading ? <Spin /> : "🚀"}
            >
              {isLoading ? "Analyzing…" : "Execute Mission"}
            </Btn>
          </div>
        </Card>
      </div>

      {/* Right Panel: Results or Empty State */}
      <div style={{ overflowY: "auto", paddingRight: 4 }}>
        {messages.length === 0 && !isLoading ? (
          <div
            style={{
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              opacity: 0.3,
              flexDirection: "column",
            }}
          >
            <div style={{ fontSize: 40, marginBottom: 10 }}>📡</div>
            <div style={{ fontSize: 12 }}>AWAITING MISSION PARAMETERS</div>
          </div>
        ) : null}

        {/* Show latest assistant message with trace in detail view */}
        {messages.length > 0 ? (
          <div className="fu">
            {messages
              .filter((m) => m.role === "assistant" && m.content)
              .map((msg, i) => (
                <Card key={i} style={{ marginBottom: 12 }}>
                  {msg.mode ? (
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 10,
                      }}
                    >
                      <Badge
                        color={MODE_BADGE_COLORS[msg.mode] || "ghost"}
                        style={{ fontSize: 10 }}
                      >
                        {msg.mode} MODE
                      </Badge>
                    </div>
                  ) : null}
                  <div
                    style={{
                      fontSize: 13,
                      lineHeight: 1.6,
                      color: "var(--t1)",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {msg.content}
                  </div>
                  {msg.trace && msg.trace.length > 0 ? (
                    <div style={{ marginTop: 12 }}>
                      <div
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          marginBottom: 8,
                          color: "var(--t3)",
                        }}
                      >
                        SYSTEM LOGS
                      </div>
                      <AgentTrace
                        steps={msg.trace.map((t) => ({
                          agent: t.name,
                          action: t.name,
                          input: t.args || "",
                          output: t.output || "",
                          citations: [],
                          status: t.status as "done" | "running" | "error",
                        }))}
                      />
                    </div>
                  ) : null}
                </Card>
              ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** Mini trace for inline chat messages */
function MiniTrace({ steps }: { steps: TraceStep[] }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      style={{
        marginTop: 8,
        borderTop: "1px solid var(--bd)",
        paddingTop: 6,
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: 10,
          color: "var(--t3)",
          fontWeight: 600,
          padding: 0,
          fontFamily: "inherit",
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
        aria-expanded={expanded}
        aria-label={`${expanded ? "Hide" : "Show"} ${steps.length} agent trace steps`}
      >
        <span>{expanded ? "▾" : "▸"}</span>
        Agent Trace
        <span style={{ fontWeight: 400, color: "var(--t3)" }}>
          {steps.length} steps
        </span>
      </button>
      {expanded ? (
        <div style={{ paddingTop: 6 }}>
          {steps.map((step, i) => (
            <div key={i} className={`agent-step ${step.status}`}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 2,
                }}
              >
                <Badge
                  color={step.status === "done" ? "green" : "accent"}
                  style={{ fontSize: 8 }}
                >
                  {step.name}
                </Badge>
                {step.status === "running" ? <Spin sz={8} /> : null}
              </div>
              <div style={{ fontSize: 10, color: "var(--t3)" }}>
                {step.args?.slice(0, 80)}
              </div>
              {step.output ? (
                <div style={{ fontSize: 10, color: "var(--t2)" }}>
                  {step.output.slice(0, 120)}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
