import { parseEventStream } from "../lib/sse";

test("parses event stream chunks", () => {
  const events = parseEventStream("data: {\"type\":\"token\",\"text\":\"hi\"}\n\n");
  expect(events[0].type).toBe("token");
});
