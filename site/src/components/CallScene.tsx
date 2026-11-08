import { useEffect, useMemo, useRef, useState } from "react";
import type { ChipState, Data, Example } from "../lib/data";
import { asset, ciText, pct, transcript } from "../lib/data";
import { alignWords, morph } from "../lib/align";
import { gsap, reducedMotion, ScrollTrigger, seg } from "../lib/motion";
import s from "./CallScene.module.css";
import { useClip } from "./useClip";
import { lerpArr, wavePath } from "./wave";

// Scroll progress -> stage. Each stage is a real, measured version of the same clip.
const STAGES = [
  { key: "clean", name: "Clean call", note: "16 kHz, as recorded", wave: "clean", at: 0 },
  { key: "bandpass", name: "Phone line", note: "300–3400 Hz band-pass", wave: "bandpass", at: 0.18 },
  { key: "phone", name: "μ-law codec", note: "8 kHz G.711 quantisation", wave: "phone", at: 0.42 },
  { key: "market_10", name: "Market noise", note: "babble at 10 dB SNR", wave: "market_10", at: 0.64 },
] as const;
const ROWS = [
  { system: "whisper", label: "Whisper-small (generic)" },
  { system: "v30", label: "Gnani Prisma v3.0" },
];
const W = 1000, H = 88;

type Frame = { stage: number; words: Record<string, { word: string; changed: boolean }[]>; cond: Record<string, string> };

function frameAt(p: number, ex: Example): { frame: Frame; wave: number[]; spec: number[][] } {
  let stage = 0;
  STAGES.forEach((st, i) => { if (p >= st.at) stage = i; });
  // waveform + spectrum: blend into the next stage over the first part of each stage
  const blends: [string, string, number][] = [
    ["clean", "bandpass", seg(p, 0.18, 0.34)],
    ["bandpass", "phone", seg(p, 0.42, 0.56)],
    ["phone", "market_10", seg(p, 0.64, 0.8)],
  ];
  let wave = ex.waveform.clean, spec = ex.spectrum.clean.db;
  for (const [a, b, t] of blends) {
    if (t <= 0) break;
    wave = lerpArr(ex.waveform[a], ex.waveform[b], t);
    spec = ex.spectrum[a].db.map((row, r) => lerpArr(row, ex.spectrum[b].db[r], t));
    if (t < 1) break;
  }
  // transcripts: ASR ran on clean, phone and market_10. Band-pass alone was not transcribed, so text holds.
  const words: Frame["words"] = {};
  const cond: Frame["cond"] = {};
  for (const r of ROWS) {
    const c = transcript(ex, r.system, "clean").text;
    const ph = transcript(ex, r.system, "phone").text;
    const mk = transcript(ex, r.system, "market_10").text;
    const t1 = seg(p, 0.44, 0.6), t2 = seg(p, 0.68, 0.92);
    if (t2 > 0) { words[r.system] = morph(alignWords(ph, mk), t2); cond[r.system] = t2 >= 1 ? "market_10" : "phone"; }
    else if (t1 > 0) { words[r.system] = morph(alignWords(c, ph), t1); cond[r.system] = t1 >= 1 ? "phone" : "clean"; }
    else { words[r.system] = c.split(/\s+/).map((w) => ({ word: w, changed: false })); cond[r.system] = "clean"; }
  }
  return { frame: { stage, words, cond }, wave, spec };
}

function drawSpec(cv: HTMLCanvasElement, db: number[][]) {
  const ctx = cv.getContext("2d");
  if (!ctx) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = cv.clientWidth, h = cv.clientHeight;
  if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const rows = db.length, cols = db[0].length;
  const cw = w / cols, rh = h / rows;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const a = Math.min(1, Math.max(0, (db[r][c] + 45) / 70)); // -45 dB -> 0, +25 dB -> 1
      ctx.fillStyle = `rgba(237,237,237,${(a * a).toFixed(3)})`;
      ctx.fillRect(c * cw, h - (r + 1) * rh, cw + 0.5, rh - 1);
    }
  }
}

function Chip({ entity, state, shown }: { entity: string; state: ChipState; shown: string | null }) {
  const kind = entity.startsWith("₹") ? "amount" : "date";
  const text = state === "missing" ? "missing" : shown ?? entity;
  return (
    <span className={s.chip} data-state={state} title={`${kind}: reference ${entity}, ${state}`}>
      <i>{kind}</i>{text}
    </span>
  );
}

export function CallScene({ data }: { data: Data }) {
  const ex = data.examples[0];
  const root = useRef<HTMLElement>(null);
  const inner = useRef<HTMLDivElement>(null);
  const path = useRef<SVGPathElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const reduced = useMemo(reducedMotion, []);
  const initial = useMemo(() => frameAt(reduced ? 1 : 0, ex), [ex, reduced]);
  const [frame, setFrame] = useState<Frame>(initial.frame);
  const lastKey = useRef("");
  const { play, stop, playing } = useClip();

  useEffect(() => {
    const render = (p: number) => {
      const { frame: f, wave, spec } = frameAt(p, ex);
      path.current?.setAttribute("d", wavePath(wave, W, H, 1.6));
      if (canvas.current) drawSpec(canvas.current, spec);
      const key = `${f.stage}|${ROWS.map((r) => f.words[r.system].map((w) => w.word).join(" ") + f.cond[r.system]).join("|")}`;
      if (key !== lastKey.current) { lastKey.current = key; setFrame(f); }
    };
    if (reduced) { render(1); return; }  // final state, no pin
    render(0);
    const mm = gsap.matchMedia();
    mm.add({ small: "(max-width: 900px)", large: "(min-width: 901px)" }, (ctx) => {
      const small = ctx.conditions?.small;
      const st = ScrollTrigger.create({
        trigger: root.current, start: "top top", end: small ? "+=170%" : "+=300%",
        pin: inner.current, scrub: true, onUpdate: (self) => render(self.progress),
      });
      return () => st.kill();
    });
    const onResize = () => render(ScrollTrigger.getAll()[0]?.progress ?? 0);
    window.addEventListener("resize", onResize);
    return () => { mm.revert(); window.removeEventListener("resize", onResize); };
  }, [ex, reduced]);

  const v30 = data.entity_by_condition.v30.market_10;
  const wh = data.entity_by_condition.whisper.market_10;
  const whClean = data.entity_by_condition.whisper.clean;

  return (
    <section ref={root} className={s.scene} aria-labelledby="call-h">
      <div ref={inner} className={s.inner}>
        <div className={`wrap ${s.grid}`}>
          <div className={s.left}>
            <h2 className={s.h2} id="call-h">A noisy line costs a generic model the money. Prisma keeps it.</h2>
            <ol className={s.stages}>
              {STAGES.map((st, i) => (
                <li key={st.key} className={s.stage} data-on={reduced || frame.stage >= i}>
                  <div className={s.stageName}>{st.name}</div>
                  <div className={s.stageNote}>{st.note}</div>
                </li>
              ))}
            </ol>
            <div className={s.listen} role="group" aria-label="Listen to this call">
              {(["clean", "market_10"] as const).map((k) => (
                <button key={k} className={s.chipBtn} aria-pressed={playing === k}
                        onClick={() => (playing === k ? stop() : play(k, asset(ex.audio[k])))}>
                  {playing === k ? "■ stop" : `▶ ${k === "clean" ? "clean" : "market, 10 dB"}`}
                </button>
              ))}
            </div>
          </div>
          <div className={s.right}>
            <div className={s.panel}>
              <div className={s.panelHead}>
                <span>clip <b>{ex.clip_id}</b></span>
                <span>now: <b>{STAGES[frame.stage].name.toLowerCase()}</b></span>
              </div>
              <svg className={s.wave} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden>
                <path ref={path} className={s.wavePath} d={wavePath(initial.wave, W, H, 1.6)} />
              </svg>
              <div className={s.specWrap}>
                <canvas ref={canvas} className={s.spec} aria-label="Spectrum by frequency band over time" role="img" />
                {/* 3.4 kHz sits between band 6 and 7 of 9 (equal-height rows) */}
                <div className={s.band} style={{ top: `${(1 - 6 / 9) * 100}%` }}><span className={s.bandLabel}>3.4 kHz</span></div>
                <div className={s.specAxis}><span>time →</span><span>0 – 8 kHz, low at bottom</span></div>
              </div>
              <div className={s.rows}>
                {ROWS.map((r) => {
                  const t = transcript(ex, r.system, frame.cond[r.system]);
                  return (
                    <div key={r.system} className={s.row}>
                      <div className={s.rowHead}>
                        <span className={s.sys}>{r.label}</span>
                        <span className={s.chips}>
                          {t.entities.map((e) => <Chip key={e.entity} entity={e.entity} state={e.state} shown={e.shown} />)}
                        </span>
                      </div>
                      <p className={s.text} lang="hi">
                        {frame.words[r.system].map((w, i) => (
                          <span key={i} className={`${s.w} ${w.changed ? s.changed : ""}`}>{w.word} </span>
                        ))}
                      </p>
                    </div>
                  );
                })}
              </div>
              <div className={s.ref} lang="hi">said: {ex.reference}</div>
            </div>
            <p className={s.caption}>
              Across all 25 calls at market noise, Prisma v3.0 got <span className={s.num}>{pct(v30.value)}</span>{" "}
              <span className={s.ci}>{ciText(v30)}</span> of amounts and dates right; Whisper-small got{" "}
              <span className={s.num}>{pct(wh.value)}</span> <span className={s.ci}>{ciText(wh)}</span>, down from{" "}
              <span className={s.num}>{pct(whClean.value)}</span> on the clean recording.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
