import { useEffect, useMemo, useRef, useState } from "react";
import type { Data } from "../lib/data";
import { gsap, reducedMotion } from "../lib/motion";
import s from "./Curves.module.css";

type Pt = { condition: string; wer: number; lo: number; hi: number; n: number;
  vs_clean: { diff: number; lo: number; hi: number; significant: boolean } | null };
type Series = { lang: string; model: string; points: Pt[] };

const MODELS = [
  { id: "prisma-v2.5", label: "Prisma v2.5", color: "#ededed" },
  { id: "prisma-v3.0", label: "Prisma v3.0", color: "#a1a1a6" },
  { id: "whisper-small", label: "Whisper-small", color: "#5a5a60" },
];
const LANGS = [["hi", "Hindi"], ["bn", "Bengali"], ["ta", "Tamil"], ["hinglish", "Hinglish"]] as const;
// x = how much noise, left to right. "clean" has no phone line; the rest are through the phone channel.
const NOISE = {
  market: [["clean", "clean"], ["phone", "phone, no noise"], ["market_10", "10 dB"], ["market_0", "0 dB"]],
  traffic: [["clean", "clean"], ["phone", "phone, no noise"], ["traffic_10", "10 dB"], ["traffic_5", "5 dB"]],
} as const;
const GEOM = {
  large: { W: 900, H: 380, PAD: { l: 52, r: 120, t: 16, b: 44 } },
  small: { W: 400, H: 330, PAD: { l: 38, r: 80, t: 12, b: 48 } },   // phone: real geometry, not a scaled-down desktop
};
function useSmall() {
  const q = "(max-width: 640px)";
  const [small, set] = useState(() => typeof window !== "undefined" && window.matchMedia(q).matches);
  useEffect(() => { const m = window.matchMedia(q); const f = () => set(m.matches); m.addEventListener("change", f); return () => m.removeEventListener("change", f); }, []);
  return small;
}

export function Curves({ data }: { data: Data }) {
  const series: Series[] = data.degradation.series;
  const [lang, setLang] = useState<string>("hi");
  const [noise, setNoise] = useState<keyof typeof NOISE>("market");
  const [tip, setTip] = useState<{ x: number; y: number; m: string; p: Pt; label: string } | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const drawn = useRef(false);
  const small = useSmall();
  const { W, H, PAD } = small ? GEOM.small : GEOM.large;
  const xs = NOISE[noise];

  const rows = useMemo(() => MODELS.map((m) => {
    const sr = series.find((x) => x.lang === lang && x.model === m.id);
    return { ...m, pts: xs.map(([c]) => sr?.points.find((p) => p.condition === c)).filter(Boolean) as Pt[] };
  }), [series, lang, xs]);
  const yMax = Math.max(0.3, ...rows.flatMap((r) => r.pts.map((p) => Math.min(p.hi, 1.4)))) * 1.05;
  const X = (i: number) => PAD.l + (i / (xs.length - 1)) * (W - PAD.l - PAD.r);
  const Y = (v: number) => PAD.t + (1 - Math.min(v, yMax) / yMax) * (H - PAD.t - PAD.b);
  const step = yMax > 0.9 ? 0.25 : yMax > 0.45 ? 0.1 : 0.05;
  const ticks = Array.from({ length: Math.floor(yMax / step) + 1 }, (_, i) => +(i * step).toFixed(2));

  // paths draw left-to-right as the chart scrolls in (noise rising); later toggles redraw instantly
  useEffect(() => {
    const paths = svg.current?.querySelectorAll<SVGPathElement>("[data-line]");
    if (!paths) return;
    paths.forEach((p) => { const L = p.getTotalLength(); p.style.strokeDasharray = `${L}`; p.style.strokeDashoffset = drawn.current || reducedMotion() ? "0" : `${L}`; });
    if (drawn.current || reducedMotion()) return;
    const tw = gsap.to(paths, { strokeDashoffset: 0, ease: "none",
      scrollTrigger: { trigger: svg.current, start: "top 75%", end: "center 45%", scrub: true, onLeave: () => { drawn.current = true; } } });
    return () => { tw.scrollTrigger?.kill(); tw.kill(); };
  }, [lang, noise, small]);

  const show = (e: React.PointerEvent | React.FocusEvent, m: string, p: Pt, i: number, label: string) => {
    if (!p) return;
    const box = svg.current!.getBoundingClientRect();
    setTip({ x: (X(i) / W) * box.width, y: (Y(p.wer) / H) * box.height, m, p, label });
    void e;
  };

  return (
    <section className={s.section} aria-labelledby="curves-h">
      <div className="wrap">
        <div className={s.head}>
          <div className={s.headL}>
            <h2 className={s.h2} id="curves-h">Prisma stays flat until the noise is as loud as the speech.</h2>
          </div>
          <p className={`${s.p} ${s.headR}`}>
            The phone line, packet loss and 10 dB noise barely move Prisma. At 0 dB market babble both Prisma
            models break. Hover or tap a point for the exact value and the paired test against clean.
          </p>
        </div>
        <div className={s.controls}>
          <div className={s.seg} role="group" aria-label="Language">
            {LANGS.map(([id, name]) => <button key={id} aria-pressed={lang === id} onClick={() => { setLang(id); setTip(null); }}>{name}</button>)}
          </div>
          <div className={s.seg} role="group" aria-label="Noise type">
            {(["market", "traffic"] as const).map((n) => <button key={n} aria-pressed={noise === n} onClick={() => { setNoise(n); setTip(null); }}>{n === "market" ? "market babble" : "street traffic"}</button>)}
          </div>
        </div>
        <div className={s.chartWrap} onPointerLeave={() => setTip(null)}>
          <svg ref={svg} className={s.svg} viewBox={`0 0 ${W} ${H}`} role="img"
               aria-label={`WER by noise level, ${lang}, ${noise}`}>
            <g className={s.grid}>{ticks.map((t) => <line key={t} x1={PAD.l} x2={W - PAD.r} y1={Y(t)} y2={Y(t)} />)}</g>
            <g className={s.axis}>
              {ticks.map((t) => <text key={t} x={PAD.l - 10} y={Y(t) + 4} textAnchor="end">{Math.round(t * 100)}%</text>)}
              {xs.map(([, l], i) => <text key={l} x={X(i)} y={H - 26} textAnchor={i === 0 ? "start" : i === xs.length - 1 ? "end" : "middle"}>{small && l.startsWith("phone") ? "phone" : l}</text>)}
              <text x={PAD.l} y={H - 4} textAnchor="start">WER, band = 95% CI · {noise} noise →</text>
            </g>
            {rows.map((r) => {
              if (r.pts.length < 2) return null;
              const band = `M${r.pts.map((p, i) => `${X(i)},${Y(p.hi)}`).join("L")}L${[...r.pts].reverse().map((p, j) => `${X(r.pts.length - 1 - j)},${Y(p.lo)}`).join("L")}Z`;
              const line = `M${r.pts.map((p, i) => `${X(i)},${Y(p.wer)}`).join("L")}`;
              const last = r.pts[r.pts.length - 1];
              return (
                <g key={r.id}>
                  <path className={s.band} d={band} fill={r.color} />
                  <path data-line className={s.path} d={line} stroke={r.color} />
                  {r.pts.map((p, i) => <circle key={i} className={s.dot} cx={X(i)} cy={Y(p.wer)} r={4.5} fill={r.color} />)}
                  {r.pts.map((p, i) => (
                    <circle key={`h${i}`} className={s.hit} cx={X(i)} cy={Y(p.wer)} r={8} tabIndex={0}
                            style={{ pointerEvents: "none" }}
                            aria-label={`${r.label}, ${xs[i][1]}: WER ${(p.wer * 100).toFixed(1)}%`}
                            onFocus={(e) => show(e, r.label, p, i, xs[i][1])} onBlur={() => setTip(null)} />
                  ))}
                  <text className={s.endLabel} x={X(r.pts.length - 1) + 12} y={Y(last.wer) + 4} fill={r.color}>{small ? r.label.replace("Prisma ", "").replace("-small", "") : r.label}</text>
                </g>
              );
            })}
            {/* one overlay finds the nearest point: overlapping curves never hide each other */}
            <rect x={PAD.l - 20} y={PAD.t} width={W - PAD.l - PAD.r + 40} height={H - PAD.t - PAD.b} fill="transparent"
                  onPointerDown={(e) => e.currentTarget.dispatchEvent(new PointerEvent("pointermove", e.nativeEvent))}
                  onPointerMove={(e) => {
                    const box = svg.current!.getBoundingClientRect();
                    const px = ((e.clientX - box.left) / box.width) * W, py = ((e.clientY - box.top) / box.height) * H;
                    const i = Math.max(0, Math.min(xs.length - 1, Math.round(((px - PAD.l) / (W - PAD.l - PAD.r)) * (xs.length - 1))));
                    let best: { r: (typeof rows)[number]; d: number } | null = null;
                    for (const r of rows) { const p = r.pts[i]; if (!p) continue; const d = Math.abs(Y(p.wer) - py); if (!best || d < best.d) best = { r, d }; }
                    if (best) show(e, best.r.label, best.r.pts[i], i, xs[i][1]);
                  }} />
          </svg>
          {tip && (
            <div className={s.tip} style={{ left: tip.x, top: tip.y }} role="status">
              <b>{tip.m}</b> · {tip.label}<br />
              WER {(tip.p.wer * 100).toFixed(1)}% [{(tip.p.lo * 100).toFixed(1)}, {(tip.p.hi * 100).toFixed(1)}] · n={tip.p.n}
              {tip.p.vs_clean && (
                <small>vs clean: {tip.p.vs_clean.diff >= 0 ? "+" : ""}{(tip.p.vs_clean.diff * 100).toFixed(1)} pts [{(tip.p.vs_clean.lo * 100).toFixed(1)}, {(tip.p.vs_clean.hi * 100).toFixed(1)}] · {tip.p.vs_clean.significant ? "significant" : "not significant"}</small>
              )}
            </div>
          )}
        </div>
        <p className={s.note}>
          25 clips per language. Hinglish WER is computed after romanisation, with Prisma v2.5 in its en-IN config;
          read Hinglish through amount accuracy above. Whisper-small writes Bengali in Devanagari, which is why its
          Bengali WER exceeds 100%.
        </p>
      </div>
    </section>
  );
}
