import type { Anomaly, AgentStep, Citation } from "./capabilities";

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
  input: Record<string, unknown>;
  output: Record<string, unknown>;
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

/** Full facility model used by the NEO frontend */
export type Facility = {
  id: string;
  name: string;
  lat: number | null;
  lng: number | null;
  city: string | null;
  region: string | null;
  address: string | null;
  facility_type: string | null;
  operator_type: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  description: string | null;
  source_url: string | null;
  capabilities: Record<string, boolean | number>;
  confidence: Record<string, number>;
  citations: Citation[];
  anomalies: Anomaly[];
  steps: AgentStep[];
  specialties_list: string[];
  equipment_list: string[];
  procedures_list: string[];
  capabilities_list: string[];
  raw: Record<string, string>;
  aiExtracted: boolean;
  _rows: number[];
};
