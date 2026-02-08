export type MapAction = {
  type: string;
  data?: Record<string, unknown>;
};

export type FacilitySummary = {
  pk_unique_id: string;
  name: string;
  lat?: number | null;
  lng?: number | null;
  facilityTypeId?: string | null;
  normalized_region?: string | null;
  address_city?: string | null;
  confidence?: number | null;
};

export type TraceEvent = {
  name: string;
  input: Record<string, any>;
  output: Record<string, any>;
};

export type ChatResponse = {
  mode: string;
  answer: string;
  citations: string[];
  map_actions: MapAction[];
  facilities: FacilitySummary[];
  trace: TraceEvent[];
};

export type SseEvent =
  | { type: "token"; text: string }
  | { type: "trace"; step: { name: string; args: string } }
  | { type: "final"; payload: ChatResponse };
