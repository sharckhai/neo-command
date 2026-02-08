"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
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

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;
    const prompt = input.trim();
    setInput("");
    setIsLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: prompt }]);
    setMessages((prev) => [...prev, { role: "assistant", content: "Thinking..." }]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: prompt, session_id: "local" }),
      });
      if (!res.body) {
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
      }
      if (buffer) {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: buffer.trim() };
          return updated;
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

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
      <div className="chat-body">
        {messages.map((msg, idx) => (
          <div key={idx} className="chat-message">
            <strong>{msg.role === "user" ? "Planner" : "VirtueCommand"}</strong>
            <div>{msg.content}</div>
          </div>
        ))}
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
        <button onClick={handleSubmit} disabled={isLoading}>
          {isLoading ? "Thinking" : "Send"}
        </button>
      </div>
    </section>
  );
}
