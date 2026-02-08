/* ══════════════════════════════════════════════════════════════════════
   Capability Schema & Rule-Based IDP Extraction
   ══════════════════════════════════════════════════════════════════════ */

export type CapMeta = {
  l: string; // label
  i: string; // icon emoji
  g: string; // group
  n?: 1;     // numeric flag (1 = value is a number)
};

export type Citation = {
  field: string;
  snippet: string;
  source: string;
  row?: number;
  step?: string;
};

export type Anomaly = {
  type: string;
  field: string;
  message: string;
  severity: "warning" | "error";
};

export type AgentStep = {
  agent: string;
  action: string;
  input: string;
  output: string;
  citations: Citation[];
  status: "done" | "running" | "error";
};

export type ExtractionResult = {
  capabilities: Record<string, boolean | number>;
  confidence: Record<string, number>;
  citations: Citation[];
  anomalies: Anomaly[];
  steps: AgentStep[];
  specialties_list: string[];
  equipment_list: string[];
  procedures_list: string[];
  capabilities_list: string[];
};

/** 28 capability definitions with label, icon, and group */
export const CAP: Record<string, CapMeta> = {
  emergency_24_7: { l: "24/7 Emergency", i: "🚨", g: "Emergency" },
  inpatient_beds: { l: "Beds", i: "🛏️", g: "Capacity", n: 1 },
  icu: { l: "ICU", i: "🏥", g: "Critical Care" },
  icu_beds: { l: "ICU Beds", i: "🏥", g: "Critical Care", n: 1 },
  nicu: { l: "NICU", i: "👶", g: "Neonatal" },
  operating_theatre: { l: "Theatre", i: "🔪", g: "Surgical" },
  theatre_count: { l: "Theatres", i: "🔪", g: "Surgical", n: 1 },
  laboratory: { l: "Lab", i: "🔬", g: "Diagnostics" },
  lab_24_7: { l: "24/7 Lab", i: "🔬", g: "Diagnostics" },
  pharmacy: { l: "Pharmacy", i: "💊", g: "Support" },
  pharmacy_24_7: { l: "24/7 Pharmacy", i: "💊", g: "Support" },
  ambulance: { l: "Ambulance", i: "🚑", g: "Emergency" },
  blood_bank: { l: "Blood Bank", i: "🩸", g: "Support" },
  xray: { l: "X-Ray", i: "☢️", g: "Imaging" },
  ultrasound: { l: "Ultrasound", i: "📺", g: "Imaging" },
  ct_scan: { l: "CT Scan", i: "📡", g: "Imaging" },
  mri: { l: "MRI", i: "🧲", g: "Imaging" },
  ecg: { l: "ECG", i: "💓", g: "Imaging" },
  mammography: { l: "Mammography", i: "🎗️", g: "Imaging" },
  endoscopy: { l: "Endoscopy", i: "🔍", g: "Diagnostics" },
  dialysis: { l: "Dialysis", i: "💧", g: "Specialty" },
  maternity: { l: "Maternity", i: "🤱", g: "Maternal" },
  csection: { l: "C-Section", i: "✂️", g: "Maternal" },
  family_planning: { l: "Family Planning", i: "👨‍👩‍👧", g: "Maternal" },
  pediatrics: { l: "Paediatrics", i: "🧒", g: "Primary" },
  dental: { l: "Dental", i: "🦷", g: "Primary" },
  ophthalmology: { l: "Eye Care", i: "👁️", g: "Specialty" },
  ent: { l: "ENT", i: "👂", g: "Specialty" },
  mental_health: { l: "Mental Health", i: "🧠", g: "Specialty" },
  physiotherapy: { l: "Physio", i: "🏃", g: "Specialty" },
  surgery_general: { l: "Surgery", i: "🩺", g: "Surgical" },
  surgery_ortho: { l: "Orthopaedic", i: "🦴", g: "Surgical" },
  surgery_neuro: { l: "Neuro", i: "🧠", g: "Surgical" },
  cardiology: { l: "Cardio", i: "❤️", g: "Specialty" },
  oncology: { l: "Oncology", i: "🎗️", g: "Specialty" },
  fertility_ivf: { l: "IVF", i: "🌱", g: "Specialty" },
  telemedicine: { l: "Telemedicine", i: "📱", g: "Technology" },
  nhis_accredited: { l: "NHIS", i: "✅", g: "Accreditation" },
  mortuary: { l: "Mortuary", i: "🏛️", g: "Support" },
};

/* ── Helpers ── */

function sj(v: string | null | undefined): string[] {
  if (!v || v === "null" || v === "[]" || v === "") return [];
  try {
    const p = JSON.parse(v);
    return Array.isArray(p)
      ? p.filter((x: unknown) => x && String(x).trim() && x !== '""')
      : [];
  } catch {
    return [];
  }
}

function cl(v: string | null | undefined): string | null {
  if (!v || v.trim().toLowerCase() === "null" || v.trim() === "") return null;
  return v.trim();
}

/* ── Specialty-to-capability mapping ── */

const SMAP: Record<string, string> = {
  internalmedicine: "internal",
  pediatrics: "pediatrics",
  cardiology: "cardiology",
  generalsurgery: "surgery_general",
  emergencymedicine: "emergency_24_7",
  orthopedicsurgery: "surgery_ortho",
  dentistry: "dental",
  ophthalmology: "ophthalmology",
  otolaryngology: "ent",
  psychiatry: "mental_health",
  neurosurgery: "surgery_neuro",
  medicaloncology: "oncology",
  neonatologyperinatalmedicine: "nicu",
  criticalcaremedicine: "icu",
  gastroenterology: "endoscopy",
  anesthesia: "operating_theatre",
};

// Hoist regex patterns outside the function per js-hoist-regexp
const SPEC_PATTERNS: [RegExp, string, number][] = [
  [/gynecol|obstet|matern/, "maternity", 0.8],
  [/pediatr/, "pediatrics", 0.8],
  [/cardio/, "cardiology", 0.8],
  [/oncol/, "oncology", 0.8],
  [/surg/, "surgery_general", 0.7],
  [/ophthal/, "ophthalmology", 0.9],
  [/denti/, "dental", 0.9],
  [/otolaryngol/, "ent", 0.9],
  [/psych/, "mental_health", 0.8],
  [/nephrol/, "dialysis", 0.5],
  [/neonat/, "nicu", 0.7],
  [/critical/, "icu", 0.7],
  [/infertil|reproductiveendocrin/, "fertility_ivf", 0.8],
  [/radiol/, "xray", 0.5],
  [/emergency/, "emergency_24_7", 0.6],
  [/orthop/, "surgery_ortho", 0.8],
  [/neurosurg/, "surgery_neuro", 0.9],
  [/physiother|rehabilit/, "physiotherapy", 0.7],
  [/family.*plan|contraception/, "family_planning", 0.7],
];

const EQUIP_PATTERNS: [RegExp, string][] = [
  [/x-?ray|xray|radiograph/, "xray"],
  [/ultrasound|ultra sound/, "ultrasound"],
  [/ct.?scan|ct.?imag/, "ct_scan"],
  [/\bmri\b/, "mri"],
  [/ecg|electrocardiog/, "ecg"],
  [/mammog/, "mammography"],
  [/endoscop/, "endoscopy"],
  [/operat|theatre|theater/, "operating_theatre"],
  [/ventilat/, "icu"],
  [/dialys/, "dialysis"],
  [/ambulanc/, "ambulance"],
  [/laborat/, "laboratory"],
  [/isolette|incubat|neonatal/, "nicu"],
  [/mortu/, "mortuary"],
  [/oct |fundus|slit.?lamp/, "ophthalmology"],
  [/dental.?chair/, "dental"],
  [/audiom|tympan/, "ent"],
  [/echocardio/, "cardiology"],
];

const PROC_PATTERNS: [RegExp, string][] = [
  [/x-?ray|xray|radiograph/, "xray"],
  [/ultrasound|scan/, "ultrasound"],
  [/\bct\b/, "ct_scan"],
  [/\bmri\b/, "mri"],
  [/ecg|electrocardiog/, "ecg"],
  [/mammog/, "mammography"],
  [/endoscop|colonoscop|gastroscop/, "endoscopy"],
  [/dialys|hemodia/, "dialysis"],
  [/surg/, "surgery_general"],
  [/c-section|caesarean|cesarean/, "csection"],
  [/ivf|in.?vitro|insemination|icsi/, "fertility_ivf"],
  [/cataract|lasik|eye.?surg/, "ophthalmology"],
  [/root.?canal|dental|filling/, "dental"],
  [/deliver|labour|labor|prenatal|antenatal/, "maternity"],
  [/physiother/, "physiotherapy"],
];

const CAP_PATTERNS: [RegExp, string][] = [
  [/nhis/, "nhis_accredited"],
  [/ambulanc/, "ambulance"],
  [/mortu/, "mortuary"],
  [/telemedicine|tele-/, "telemedicine"],
  [/\bicu\b(?!.*nicu)/, "icu"],
  [/nicu|neonatal.?intensive/, "nicu"],
  [/blood.?bank/, "blood_bank"],
  [/pharmacy/, "pharmacy"],
  [/laborat/, "laboratory"],
  [/maternity|delivery.?ward|labour.?ward/, "maternity"],
  [/operating.?theat|operating.?room/, "operating_theatre"],
  [/dialys/, "dialysis"],
];

/**
 * 5-step IDP extraction pipeline with per-step citation tracking.
 * Returns capabilities, confidence, citations, anomalies, and pipeline steps.
 */
export function ruleExtract(
  row: Record<string, string>,
  rowIndex: number
): ExtractionResult {
  const specs = sj(row.specialties);
  const equip = sj(row.equipment);
  const procs = sj(row.procedure);
  const caps = sj(row.capability);
  const desc = cl(row.description) || "";
  const allText = [...equip, ...procs, ...caps, desc].join(" ").toLowerCase();

  const c: Record<string, boolean | number> = {};
  const cf: Record<string, number> = {};
  const cit: Citation[] = [];
  const steps: AgentStep[] = [];

  const set = (
    k: string,
    v: boolean | number,
    conf: number,
    src: string,
    step: string
  ): void => {
    if (c[k] === undefined || conf > (cf[k] || 0)) {
      c[k] = v;
      cf[k] = conf;
      cit.push({
        field: k,
        snippet: src.slice(0, 180),
        source: "csv",
        row: rowIndex,
        step,
      });
    }
  };

  // ── IDP Step 1: Specialty Tokenization ──
  specs.forEach((s) => {
    const sl = s.toLowerCase().replace(/\s/g, "");
    if (SMAP[sl]) set(SMAP[sl], true, 0.7, `Specialty: ${s}`, "specialty_parse");
    for (const [re, k, cf2] of SPEC_PATTERNS) {
      if (re.test(sl)) set(k, true, cf2, `Specialty: ${s}`, "specialty_parse");
    }
  });
  steps.push({
    agent: "TokenizerAgent",
    action: "Parse specialties",
    input: `${specs.length} specialties`,
    output: `Mapped ${specs.length} → ${Object.keys(c).length} capabilities`,
    citations: cit.filter((x) => x.step === "specialty_parse"),
    status: "done",
  });

  // ── IDP Step 2: Equipment NER ──
  const eqBefore = Object.keys(c).length;
  equip.forEach((e) => {
    const el = e.toLowerCase();
    for (const [re, k] of EQUIP_PATTERNS) {
      if (re.test(el)) set(k, true, 1.0, e, "equipment_ner");
    }
  });
  steps.push({
    agent: "NERAgent",
    action: "Extract from equipment",
    input: `${equip.length} equipment items`,
    output: `Found ${Object.keys(c).length - eqBefore} new capabilities`,
    citations: cit.filter((x) => x.step === "equipment_ner"),
    status: "done",
  });

  // ── IDP Step 3: Procedure Classification ──
  const prBefore = Object.keys(c).length;
  procs.forEach((p) => {
    const pl = p.toLowerCase();
    for (const [re, k] of PROC_PATTERNS) {
      if (re.test(pl)) set(k, true, 1.0, p, "procedure_classify");
    }
  });
  steps.push({
    agent: "ClassifierAgent",
    action: "Classify procedures",
    input: `${procs.length} procedures`,
    output: `Found ${Object.keys(c).length - prBefore} new capabilities`,
    citations: cit.filter((x) => x.step === "procedure_classify"),
    status: "done",
  });

  // ── IDP Step 4: Capability Semantic Extraction ──
  const capBefore = Object.keys(c).length;
  caps.forEach((cap) => {
    const cl2 = cap.toLowerCase();
    if (cl2.includes("24/7") || cl2.includes("24 hour") || cl2.includes("always open")) {
      if (cl2.includes("emergency") || cl2.includes("accident"))
        set("emergency_24_7", true, 1.0, cap, "capability_extract");
      if (cl2.includes("lab"))
        set("lab_24_7", true, 1.0, cap, "capability_extract");
      if (cl2.includes("pharm"))
        set("pharmacy_24_7", true, 1.0, cap, "capability_extract");
    }
    for (const [re, k] of CAP_PATTERNS) {
      if (re.test(cl2)) set(k, true, 0.9, cap, "capability_extract");
    }
    const bedM = cl2.match(/(\d+)[\s-]*bed/);
    if (bedM) set("inpatient_beds", parseInt(bedM[1]), 0.9, cap, "capability_extract");
    const icuM = cl2.match(/(\d+)\s*icu\s*bed/);
    if (icuM) set("icu_beds", parseInt(icuM[1]), 0.9, cap, "capability_extract");
    const thM = cl2.match(/(\d+)\s*(?:operat|theat)/);
    if (thM) set("theatre_count", parseInt(thM[1]), 0.9, cap, "capability_extract");
  });
  if (allText.includes("pharmacy"))
    set("pharmacy", true, 0.4, desc.slice(0, 100), "capability_extract");
  if (allText.includes("laboratory") || allText.includes("lab test"))
    set("laboratory", true, 0.4, desc.slice(0, 100), "capability_extract");
  steps.push({
    agent: "SemanticAgent",
    action: "Extract from capabilities & description",
    input: `${caps.length} capabilities + description`,
    output: `Found ${Object.keys(c).length - capBefore} new capabilities`,
    citations: cit.filter((x) => x.step === "capability_extract"),
    status: "done",
  });

  // ── IDP Step 5: Anomaly Detection / Verification ──
  const anomalies: Anomaly[] = [];
  const fType = (cl(row.facilityTypeId) || "").toLowerCase();

  if (fType === "hospital") {
    if (!c.laboratory)
      anomalies.push({ type: "missing_expected", field: "laboratory", message: "Hospital without lab", severity: "warning" });
    if (!c.pharmacy)
      anomalies.push({ type: "missing_expected", field: "pharmacy", message: "Hospital without pharmacy", severity: "warning" });
  }
  if (c.surgery_general && !c.operating_theatre)
    anomalies.push({ type: "conflict", field: "surgery_general", message: "Surgery without operating theatre", severity: "warning" });
  if (c.csection && !c.operating_theatre)
    anomalies.push({ type: "conflict", field: "csection", message: "C-section without operating theatre", severity: "warning" });
  if (c.icu && !c.inpatient_beds)
    anomalies.push({ type: "conflict", field: "icu", message: "ICU without bed count", severity: "warning" });
  if (c.nicu && !c.maternity)
    anomalies.push({ type: "conflict", field: "nicu", message: "NICU without maternity", severity: "warning" });
  if (c.dialysis && !c.laboratory)
    anomalies.push({ type: "conflict", field: "dialysis", message: "Dialysis without lab", severity: "warning" });
  if (fType === "clinic" && (c.ct_scan || c.mri)) {
    const f2 = c.ct_scan ? "ct_scan" : "mri";
    if ((cf[f2] || 0) < 0.8)
      anomalies.push({ type: "high_claim", field: f2, message: `Clinic claims ${f2} (low evidence)`, severity: "error" });
  }

  steps.push({
    agent: "VerifierAgent",
    action: "Cross-reference & anomaly detection",
    input: `${Object.keys(c).length} capabilities, facility type: ${fType}`,
    output: `${anomalies.length} anomalies detected`,
    citations: anomalies.map((a) => ({
      field: a.field,
      snippet: a.message,
      source: "rule",
      step: "verify",
    })),
    status: "done",
  });

  return {
    capabilities: c,
    confidence: cf,
    citations: cit,
    anomalies,
    steps,
    specialties_list: specs,
    equipment_list: equip,
    procedures_list: procs,
    capabilities_list: caps,
  };
}
