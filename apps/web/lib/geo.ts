/* ══════════════════════════════════════════════════════════════════════
   Ghana Geocoding Lookup Tables
   Accra neighborhoods → city-level → region-level fallback
   ══════════════════════════════════════════════════════════════════════ */

type CoordPair = [number, number];
type CoordMap = Record<string, CoordPair>;

// Accra neighborhoods for sub-city resolution
const GN: CoordMap = {
  osu: [5.556, -0.177], labone: [5.561, -0.174], "east legon": [5.635, -0.155],
  cantonments: [5.575, -0.17], airport: [5.605, -0.17], "airport residential": [5.601, -0.168],
  "airport city": [5.599, -0.172], roman: [5.573, -0.192], ridge: [5.56, -0.2],
  adabraka: [5.56, -0.21], kokomlemle: [5.57, -0.205], "north ridge": [5.563, -0.204],
  "west ridge": [5.558, -0.208], tesano: [5.59, -0.23], dansoman: [5.548, -0.259],
  darkuman: [5.57, -0.25], kaneshie: [5.57, -0.222], abeka: [5.582, -0.23],
  lapaz: [5.6, -0.24], achimota: [5.62, -0.23], dzorwulu: [5.6, -0.2],
  abelemkpe: [5.61, -0.2], "north legon": [5.655, -0.185], legon: [5.65, -0.19],
  madina: [5.68, -0.17], haatso: [5.66, -0.21], taifa: [5.645, -0.25],
  dome: [5.65, -0.23], kwabenya: [5.71, -0.22], ashongman: [5.7, -0.21],
  agbogba: [5.67, -0.18], adenta: [5.72, -0.16], ashale: [5.67, -0.13],
  "ashale-botwe": [5.67, -0.13], nungua: [5.59, -0.07], spintex: [5.64, -0.07],
  sakumono: [5.635, -0.03], lashibi: [5.64, -0.04], teshie: [5.575, -0.1],
  labadi: [5.56, -0.15], nima: [5.58, -0.2], maamobi: [5.578, -0.208],
  newtown: [5.57, -0.212], "accra newtown": [5.57, -0.212], circle: [5.57, -0.21],
  "kwame nkrumah": [5.555, -0.205], jamestown: [5.538, -0.208], usshertown: [5.541, -0.205],
  "osu oxford": [5.555, -0.177], mataheko: [5.564, -0.21], pig: [5.56, -0.21],
  "tantra hill": [5.632, -0.228], pokuase: [5.67, -0.3], amasaman: [5.7, -0.3],
  weija: [5.56, -0.33], kasoa: [5.53, -0.42], oyarifa: [5.71, -0.155],
  abokobi: [5.73, -0.17], parakuo: [5.645, -0.235], "community 25": [5.68, -0.01],
  "tema community": [5.67, -0.01], ring: [5.56, -0.205], "ring road": [5.56, -0.205],
  liberation: [5.57, -0.185], "east cantonments": [5.58, -0.162], baatsona: [5.64, -0.06],
  "adenta municipality": [5.72, -0.16], "accra central": [5.55, -0.2],
  kwadaso: [6.688, -1.645], atonsu: [6.66, -1.64], bantama: [6.7, -1.63],
  suame: [6.71, -1.62], asafo: [6.695, -1.615], adum: [6.692, -1.618],
  nhyiaeso: [6.685, -1.628], oforikrom: [6.682, -1.612], ayigya: [6.69, -1.59],
  "kumasi south": [6.66, -1.63], dichemso: [6.7, -1.64],
  "tema community 1": [5.675, -0.015], "tema community 2": [5.67, -0.01],
};

// Ghana city-level coordinates
const GC: CoordMap = {
  accra: [5.6, -0.19], kumasi: [6.69, -1.624], tema: [5.67, -0.017],
  takoradi: [4.898, -1.76], tamale: [9.408, -0.839], "cape coast": [5.104, -1.247],
  sunyani: [7.335, -2.327], koforidua: [6.094, -0.257], ho: [6.601, 0.471],
  techiman: [7.585, -1.938], tarkwa: [5.305, -1.993], obuasi: [6.202, -1.662],
  wa: [10.06, -2.51], bolgatanga: [10.786, -0.851], ashaiman: [5.687, -0.035],
  berekum: [7.453, -2.585], yendi: [9.445, -0.01], osu: [5.556, -0.177],
  "east legon": [5.635, -0.155], dansoman: [5.548, -0.259], madina: [5.68, -0.17],
  dome: [5.65, -0.23], cantonments: [5.575, -0.17], adenta: [5.72, -0.16],
  dodowa: [5.88, -0.09], nungua: [5.59, -0.07], worawora: [7.25, 0.37],
  bechem: [7.09, -2.03], apremdo: [4.87, -1.73], somanya: [6.1, -0.02],
  damongo: [9.08, -1.82], nkwanta: [8.26, 0.51], dzodze: [6.34, 0.65],
  dompoase: [6.54, -1.63], "accra newtown": [5.57, -0.212], juaso: [6.6, -1.1],
  pokoase: [5.67, -0.3], "adenta-fafraha": [5.72, -0.15],
  "darkuman-nyamekye": [5.57, -0.25], mankessim: [5.276, -1.021],
  hohoe: [7.15, 0.47], acherensua: [7.07, -2.33], achimota: [5.62, -0.23],
  abesim: [7.32, -2.34], atebubu: [7.75, -0.98], "zabzugu tatale": [9.66, 0.02],
  bawku: [11.06, -0.24], navrongo: [10.89, -1.09], keta: [5.92, 0.99],
  kasoa: [5.53, -0.42], aflao: [6.12, 1.19], akosombo: [6.29, 0.04],
  amasaman: [5.7, -0.3], ankaful: [5.12, -1.25], nsawam: [5.81, -0.349],
  winneba: [5.351, -0.625], saltpond: [5.21, -1.06], elmina: [5.08, -1.35],
  kpando: [6.99, 0.29], effiduase: [6.74, -1.41], ejisu: [6.7, -1.46],
  nkawie: [6.73, -1.75], bole: [9.03, -2.49], gushegu: [9.87, -0.09],
  savelugu: [9.62, -0.83], bimbilla: [9.59, 0.05], salaga: [8.55, -0.51],
  kintampo: [8.05, -1.73], nkoranza: [7.55, -1.72], wenchi: [7.74, -2.1],
  konongo: [6.62, -1.22], nkawkaw: [6.56, -0.77], kibi: [6.16, -0.55],
  aburi: [5.85, -0.17], akropong: [5.97, -0.08], suhum: [6.04, -0.45],
  dunkwa: [5.96, -1.78], prestea: [5.43, -2.14], axim: [4.87, -2.24],
  sekondi: [4.92, -1.71], jasikan: [7.4, 0.45], dambai: [7.96, 0.19],
  bogoso: [5.53, -2.1], pokuase: [5.67, -0.3], weija: [5.56, -0.33],
  lapaz: [5.6, -0.24], darkuman: [5.57, -0.25], kaneshie: [5.57, -0.222],
  nima: [5.58, -0.2], legon: [5.65, -0.19], haatso: [5.66, -0.21],
  taifa: [5.645, -0.25], spintex: [5.64, -0.07], sakumono: [5.635, -0.03],
  kpone: [5.7, 0.02], "accra central": [5.55, -0.2], "greater accra": [5.6, -0.19],
  "agona swedru": [5.53, -0.7], asamankese: [5.87, -0.67],
  "asokore mampong": [6.71, -1.6], agbogba: [5.67, -0.18], adidome: [6.1, 0.47],
  akatsi: [6.13, 0.8], akwatia: [6.04, -0.8], anloga: [5.79, 0.9],
  mampong: [7.06, -1.4], offinso: [7.07, -1.65], ejura: [7.38, -1.36],
  agogo: [6.8, -1.08], tesano: [5.59, -0.23], kwadaso: [6.688, -1.645],
  oyarifa: [5.71, -0.155], battor: [6.04, 0.35], bibiani: [6.46, -2.32],
  sogakope: [6.01, 0.597], tepa: [7.064, -1.893], "agona nkwanta": [5.87, -1.04],
  kwahu: [6.62, -0.78], "sekondi-takoradi": [4.91, -1.76], goaso: [6.8, -2.52],
  abokobi: [5.73, -0.17],
};

// Ghana region-level coordinates
export const GR: CoordMap = {
  "greater accra": [5.6, -0.19], "greater accra region": [5.6, -0.19],
  ashanti: [6.75, -1.52], "ashanti region": [6.75, -1.52],
  western: [5.1, -2.0], "western region": [5.1, -2.0],
  central: [5.45, -1.0], "central region": [5.45, -1.0],
  eastern: [6.25, -0.5], "eastern region": [6.25, -0.5],
  volta: [6.8, 0.5], "volta region": [6.8, 0.5],
  northern: [9.5, -1.0], "northern region": [9.5, -1.0],
  "upper east": [10.7, -1.0], "upper east region": [10.7, -1.0],
  "upper west": [10.25, -2.15], "upper west region": [10.25, -2.15],
  "brong ahafo": [7.5, -1.5], "brong ahafo region": [7.5, -1.5],
  "bono east": [7.75, -1.05], "bono east region": [7.75, -1.05],
  ahafo: [6.9, -2.3], "ahafo region": [6.9, -2.3],
  bono: [7.5, -2.3],
  oti: [7.8, 0.3], "oti region": [7.8, 0.3],
  "western north": [6.3, -2.5], "western north region": [6.3, -2.5],
  "north east": [10.2, -0.3],
  savannah: [9.0, -1.8], "savannah region": [9.0, -1.8],
  "ga east": [5.67, -0.23], "ga east municipality": [5.67, -0.23],
  "ga west": [5.63, -0.31],
};

// Seeded jitter: spreads co-located facilities in a deterministic spiral
const jitterCache: Record<string, number> = {};

function jitter(lat: number, lng: number): CoordPair {
  const key = `${lat.toFixed(3)},${lng.toFixed(3)}`;
  if (!jitterCache[key]) jitterCache[key] = 0;
  const n = jitterCache[key]++;
  if (n === 0) return [lat, lng];
  // Golden-angle spiral
  const r = 0.004 + 0.002 * Math.sqrt(n);
  const a = n * 2.3999;
  return [lat + r * Math.cos(a), lng + r * Math.sin(a)];
}

export function resetJitterCache(): void {
  for (const k of Object.keys(jitterCache)) {
    delete jitterCache[k];
  }
}

/**
 * Geocode a facility by checking neighborhood → city → region.
 * Returns [lat, lng] or [null, null] if no match.
 */
export function geo(
  city: string | null | undefined,
  region: string | null | undefined,
  addr2: string | null | undefined
): [number, number] | [null, null] {
  // Try address_line2 neighborhood first
  if (addr2 && addr2.toLowerCase().trim() !== "null") {
    const nk = addr2.toLowerCase().trim().replace(/,.*$/, "").trim();
    if (GN[nk]) return jitter(...GN[nk]);
    const nk2 = nk.split(" ")[0];
    if (GN[nk2]) return jitter(...GN[nk2]);
  }
  // Try city
  if (city && city.toLowerCase().trim() !== "null") {
    const k = city.toLowerCase().trim();
    if (GC[k]) return jitter(...GC[k]);
    const f = k.split(",")[0].split("-")[0].trim();
    if (GC[f]) return jitter(...GC[f]);
    if (GN[k]) return jitter(...GN[k]);
  }
  // Try region
  if (region && region.toLowerCase().trim() !== "null") {
    const k = region.toLowerCase().trim();
    if (GR[k]) return jitter(...GR[k]);
  }
  return [null, null];
}
