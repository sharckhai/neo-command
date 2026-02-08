/* ══════════════════════════════════════════════════════════════════════
   CSV Parsing, Deduplication & IDP Extraction
   ══════════════════════════════════════════════════════════════════════ */

import Papa from "papaparse";
import { geo, resetJitterCache } from "./geo";
import { ruleExtract } from "./capabilities";
import type { Facility } from "./types";

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

type RawRow = Record<string, string> & { _rowIndex: number };

/**
 * Parse a CSV string into deduplicated, geocoded, IDP-extracted facilities.
 * Multi-row facilities (same pk_unique_id) are merged.
 */
export function parseCSV(csvText: string): Facility[] {
  resetJitterCache();

  const { data } = Papa.parse<Record<string, string>>(csvText, {
    header: true,
    skipEmptyLines: true,
  });

  // Group rows by pk_unique_id
  const groups: Record<string, RawRow[]> = {};
  data.forEach((r, i) => {
    const pk = r.pk_unique_id || r.name || String(i);
    if (!groups[pk]) groups[pk] = [];
    groups[pk].push({ ...r, _rowIndex: i + 2 } as RawRow);
  });

  return Object.entries(groups).map(([pk, rows]) => {
    const base: Record<string, string> = { ...rows[0] };

    // Merge multi-row facilities
    if (rows.length > 1) {
      const sets = {
        s: new Set<string>(),
        e: new Set<string>(),
        p: new Set<string>(),
        c: new Set<string>(),
        d: new Set<string>(),
      };
      for (const r of rows) {
        for (const x of sj(r.specialties)) sets.s.add(x);
        for (const x of sj(r.equipment)) sets.e.add(x);
        for (const x of sj(r.procedure)) sets.p.add(x);
        for (const x of sj(r.capability)) sets.c.add(x);
        const d = cl(r.description);
        if (d) sets.d.add(d);

        const mergeFields = [
          "address_city", "address_stateOrRegion", "address_line1",
          "email", "officialWebsite", "facilityTypeId", "operatorTypeId",
          "capacity", "numberDoctors",
        ];
        for (const k of mergeFields) {
          if (cl(r[k]) && !cl(base[k])) base[k] = r[k];
        }
      }
      base.specialties = JSON.stringify([...sets.s]);
      base.equipment = JSON.stringify([...sets.e]);
      base.procedure = JSON.stringify([...sets.p]);
      base.capability = JSON.stringify([...sets.c]);
      if (sets.d.size) base.description = [...sets.d].join(" | ");
    }

    const city = cl(base.address_city);
    const region = cl(base.address_stateOrRegion);
    const addr2 = cl(base.address_line2);
    const [lat, lng] = geo(city, region, addr2);
    const phones = sj(base.phone_numbers);
    const addr = [cl(base.address_line1), cl(base.address_line2), cl(base.address_line3)]
      .filter(Boolean)
      .join(", ");

    const ext = ruleExtract(base, rows[0]._rowIndex);

    return {
      id: pk,
      name: cl(base.name) || `Facility_${pk}`,
      lat,
      lng,
      city,
      region,
      address: addr || null,
      facility_type: cl(base.facilityTypeId),
      operator_type: cl(base.operatorTypeId),
      phone: phones.slice(0, 2).join(", ") || null,
      email: cl(base.email),
      website: cl(base.officialWebsite),
      description: cl(base.description),
      source_url: cl(base.source_url),
      ...ext,
      raw: base,
      aiExtracted: false,
      _rows: rows.map((r) => r._rowIndex),
    };
  });
}
