"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { parseEventStream } from "../lib/sse";
import { ChatResponse, TraceEvent } from "../lib/types";

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

const STARTER_PROMPTS = [
  { label: "Explore", prompt: "How many facilities offer cardiology?" },
  { label: "Verify", prompt: "Which facilities have suspicious capability claims?" },
  { label: "Plan", prompt: "I have 2 ophthalmologists for 10 days. Where should I send them?" },
];

const MODE_COLORS: Record<string, string> = {
  EXPLORE: "badge-explore",
  VERIFY: "badge-verify",
  PLAN: "badge-plan",
};

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Ask about facilities, verify claims, or plan a mission. I will keep the map in sync.",
    },
  ]);
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
                { name: event.step.name, args: event.step.args, status: "running" },
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
              const completedTrace: TraceStep[] = (event.payload.trace ?? []).map(
                (t: TraceEvent) => ({
                  name: t.name,
                  args: JSON.stringify(t.input).slice(0, 120),
                  output: JSON.stringify(t.output).slice(0, 200),
                  status: "done" as const,
                })
              );
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: event.payload.answer,
                  mode: event.payload.mode,
                  trace: completedTrace.length ? completedTrace : traceSteps.map((s) => ({ ...s, status: "done" as const })),
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

  const showStarters = messages.length === 1 && !isLoading;

  return (
    <section className="panel chat-panel">
      <div className="chat-header">
        <span>Live Mission Desk</span>
        <h1>VirtueCommand</h1>
        <p>
          Turn messy facility data into confident deployment decisions, with transparent
          evidence.
        </p>
        <div className="tag-row">
          <span className="tag">Explore</span>
          <span className="tag">Verify</span>
          <span className="tag">Plan</span>
        </div>
      </div>
      <div className="chat-body" ref={chatBodyRef}>
        {messages.map((msg, idx) => (
          <div key={idx} className="chat-message">
            <div className="chat-message-header">
              <strong>{msg.role === "user" ? "Planner" : "VirtueCommand"}</strong>
              {msg.mode && (
                <span className={`mode-badge ${MODE_COLORS[msg.mode] ?? ""}`}>
                  {msg.mode}
                </span>
              )}
            </div>
            {msg.role === "assistant" ? (
              <div className="markdown-content">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            ) : (
              <div>{msg.content}</div>
            )}
            {msg.trace && msg.trace.length > 0 && (
              <TracePanel steps={msg.trace} />
            )}
          </div>
        ))}
        {isLoading && messages[messages.length - 1]?.content === "" && (
          <div className="thinking-indicator">Thinking...</div>
        )}
        {showStarters && (
          <div className="starter-prompts">
            {STARTER_PROMPTS.map((sp) => (
              <button
                key={sp.label}
                className="starter-btn"
                onClick={() => handleSubmit(sp.prompt)}
              >
                <span className="starter-label">{sp.label}</span>
                <span className="starter-text">{sp.prompt}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="chat-input">
        <input
          placeholder="Ask about surgical deserts, ICU coverage, or mission targets"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              handleSubmit();
            }
          }}
        />
        <button onClick={() => handleSubmit()} disabled={isLoading}>
          {isLoading ? "Thinking" : "Send"}
        </button>
      </div>
    </section>
  );
}

function TracePanel({ steps }: { steps: TraceStep[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="trace-panel">
      <button className="trace-toggle" onClick={() => setExpanded(!expanded)}>
        <span className="trace-toggle-icon">{expanded ? "▾" : "▸"}</span>
        <span>Agent Trace</span>
        <span className="trace-count">{steps.length} steps</span>
      </button>
      {expanded && (
        <div className="trace-steps">
          {steps.map((step, i) => (
            <div key={i} className={`agent-step ${step.status}`}>
              <div className="agent-step-header">
                <span className={`agent-badge ${step.status}`}>{step.name}</span>
                {step.status === "running" && <span className="spin" />}
              </div>
              <div className="agent-step-args">
                <b>Input:</b> {step.args?.slice(0, 120)}
              </div>
              {step.output && (
                <div className="agent-step-output">
                  <b>Output:</b> {step.output?.slice(0, 200)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
