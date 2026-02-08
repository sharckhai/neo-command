import { ChatResponse, SseEvent } from "./types";

export function parseEventStream(chunk: string): SseEvent[] {
  const events: SseEvent[] = [];
  const blocks = chunk.split("\n\n").map((block) => block.trim());
  for (const block of blocks) {
    if (!block) continue;
    const dataLine = block
      .split("\n")
      .find((line) => line.trim().startsWith("data:"));
    if (!dataLine) continue;
    const payloadText = dataLine.replace(/^data:\s*/, "").trim();
    if (!payloadText) continue;
    try {
      const parsed = JSON.parse(payloadText) as SseEvent;
      if (parsed.type === "token" || parsed.type === "trace" || parsed.type === "final") {
        events.push(parsed);
      }
    } catch {
      // ignore malformed
    }
  }
  return events;
}

export function extractFinalPayload(events: SseEvent[]): ChatResponse | null {
  for (const event of events) {
    if (event.type === "final") {
      return event.payload;
    }
  }
  return null;
}
