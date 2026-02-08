/* ══════════════════════════════════════════════════════════════════════
   TF-IDF RAG Index — Client-side vector search, no API needed
   ══════════════════════════════════════════════════════════════════════ */

import type { Facility } from "./types";

type TFIDFVec = Record<string, number>;

export class TFIDFIndex {
  private docs: string[][] = [];
  private idf: Record<string, number> = {};
  private tfidf: TFIDFVec[] = [];

  private tokenize(text: string): string[] {
    return (text || "")
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, "")
      .split(/\s+/)
      .filter((t) => t.length > 2);
  }

  build(facilities: Facility[]): void {
    this.docs = facilities.map((f) => {
      const text = [
        f.name,
        f.city,
        f.region,
        f.facility_type,
        ...(f.specialties_list || []),
        ...(f.equipment_list || []),
        ...(f.procedures_list || []),
        ...(f.capabilities_list || []),
        f.description || "",
      ].join(" ");
      return this.tokenize(text);
    });

    // Compute IDF
    const N = this.docs.length;
    const df: Record<string, number> = {};
    for (const d of this.docs) {
      const seen = new Set(d);
      for (const t of seen) {
        df[t] = (df[t] || 0) + 1;
      }
    }
    this.idf = {};
    for (const t of Object.keys(df)) {
      this.idf[t] = Math.log(N / (df[t] + 1)) + 1;
    }

    // Compute TF-IDF vectors
    this.tfidf = this.docs.map((d) => {
      const tf: Record<string, number> = {};
      const len = d.length;
      for (const t of d) {
        tf[t] = (tf[t] || 0) + 1 / len;
      }
      const vec: TFIDFVec = {};
      for (const t of Object.keys(tf)) {
        vec[t] = tf[t] * (this.idf[t] || 0);
      }
      return vec;
    });
  }

  search(query: string, topK = 10): { index: number; score: number }[] {
    const qtokens = this.tokenize(query);
    const qtf: Record<string, number> = {};
    const qlen = qtokens.length;
    if (qlen === 0) return [];

    for (const t of qtokens) {
      qtf[t] = (qtf[t] || 0) + 1 / qlen;
    }
    const qvec: TFIDFVec = {};
    for (const t of Object.keys(qtf)) {
      qvec[t] = qtf[t] * (this.idf[t] || 0);
    }

    const scores = this.tfidf.map((dv, i) => {
      let dot = 0;
      let dNorm = 0;
      let qNorm = 0;
      const allKeys = new Set([...Object.keys(dv), ...Object.keys(qvec)]);
      for (const k of allKeys) {
        const a = dv[k] || 0;
        const b = qvec[k] || 0;
        dot += a * b;
        dNorm += a * a;
        qNorm += b * b;
      }
      return {
        index: i,
        score: dNorm && qNorm ? dot / Math.sqrt(dNorm * qNorm) : 0,
      };
    });

    return scores
      .filter((s) => s.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, topK);
  }
}

/** Singleton RAG index instance shared across the app */
export const ragIndex = new TFIDFIndex();
