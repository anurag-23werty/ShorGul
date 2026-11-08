// Types for site/public/data.json (written by scripts/export_site_data.py). Nothing on the page is hardcoded.
export type CI = { value: number | null; lo: number | null; hi: number | null };
export type Paired = { diff: number; lo: number; hi: number; p: number; significant: boolean; verdict: string; n_clips: number } | null;
export type ChipState = "written" | "spoken" | "garbled" | "missing";
export type EntityChip = { entity: string; state: ChipState; shown: string | null; after_repair: boolean };
export type Transcript = { system: string; condition: string; text: string; repaired: string; wer: number; entities: EntityChip[] };
export type Spectrum = { edges_hz: number[]; db: number[][] };
export type Example = {
  clip_id: string; reference: string; entities: string[]; duration_s: number;
  audio: Record<string, string>; waveform: Record<string, number[]>; spectrum: Record<string, Spectrum>;
  transcripts: Transcript[]; note: string;
};
export type System = { id: string; label: string; model: string; variant: string };
export type Data = {
  generated_at: string; ci: string;
  headline: {
    framing: string; entity_v25_en: CI; entity_v25_hi: CI; entity_v30: CI;
    matched_v30_minus_v25: Record<string, Paired>; note: string;
  };
  systems: System[];
  entity_by_condition: Record<string, Record<string, CI & { n: number }>>;
  rankings: any; degradation: any; repair: any; terminals: any; pipeline: any; validation: any;
  conditions: any; findings: any;
  examples: Example[];
};

export async function loadData(): Promise<Data> {
  const res = await fetch(`${import.meta.env.BASE_URL}data.json`);
  if (!res.ok) throw new Error(`data.json: HTTP ${res.status}`);
  return res.json();
}

export const asset = (p: string) => `${import.meta.env.BASE_URL}${p}`;
export const pct = (v: number | null | undefined, digits = 0) =>
  v == null ? "–" : `${(v * 100).toFixed(digits)}%`;
export const ciText = (c: CI, digits = 0) =>
  c.lo == null || c.hi == null ? "" : `[${(c.lo * 100).toFixed(digits)}, ${(c.hi * 100).toFixed(digits)}]`;
export const transcript = (ex: Example, system: string, condition: string) =>
  ex.transcripts.find((t) => t.system === system && t.condition === condition)!;
