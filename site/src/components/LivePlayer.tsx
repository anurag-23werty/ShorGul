import { useCallback, useEffect, useRef, useState } from "react";
import type { Data } from "../lib/data";
import { asset } from "../lib/data";
import { reducedMotion } from "../lib/rm";
import s from "./LivePlayer.module.css";

type Tr = { system: string; label: string; words: string[]; t: number[]; marks: (string | null)[] };
type Cond = { id: string; audio: string; peaks: number[]; transcripts: Tr[] };
const LABEL: Record<string, string> = { clean: "clean", phone: "phone", market_0: "market 0 dB" };
const INK = "#ededed", BAR = "#8e8e93", BAR_OFF = "#3a3a3e", LINE = "#55555a";
// deterministic per-column hash noise: the idle trace gets a real noise floor as you scroll, no Math.random flicker
const hash = (n: number) => { const x = Math.sin(n * 12.9898) * 43758.5453; return x - Math.floor(x); };

/** Hero player. Idle: the real clip's waveform, getting noisier as you scroll the first screen.
 *  Playing: all three real versions play in sync; the toggle switches what you hear instantly, and an
 *  AnalyserNode draws exactly that signal. Transcript words appear at (approximate) speech time. */
export function LivePlayer({ data, onReady }: { data: Data; onReady?: (play: () => void) => void }) {
  const live = data.live;
  const conds: Cond[] = live.conditions;
  const [cond, setCond] = useState("clean");
  const [playing, setPlaying] = useState(false);
  const [t, setT] = useState(Infinity);
  const wave = useRef<HTMLCanvasElement>(null);
  const spec = useRef<HTMLCanvasElement>(null);
  const audio = useRef<{ ctx: AudioContext; gains: Record<string, GainNode>; an: AnalyserNode; bufs: Record<string, AudioBuffer>;
    srcs: AudioBufferSourceNode[]; t0: number } | null>(null);
  const condRef = useRef(cond);
  const scrollP = useRef(0);
  condRef.current = cond;

  // ---- drawing ------------------------------------------------------------------------------------------
  const fit = (cv: HTMLCanvasElement) => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2), w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    const ctx = cv.getContext("2d")!; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
    return { ctx, w, h };
  };
  const drawIdle = useCallback((phase: number) => {
    const cv = wave.current; if (!cv) return;
    const { ctx, w, h } = fit(cv);
    const a = conds[0].peaks, b = conds[2].peaks, mix = scrollP.current, n = a.length;
    ctx.strokeStyle = INK; ctx.lineWidth = 1.5; ctx.beginPath();
    const cols = Math.floor(w / 2);
    for (let x = 0; x < cols; x++) {
      const i = Math.floor((x / cols) * n + phase) % n;           // slow drift through the real envelope
      const amp = (a[i] * (1 - mix) + b[i] * mix) * (h / 2 - 4);
      const noise = (hash(x + Math.floor(phase * 20) * 997) - 0.5) * mix * (h - 8) * 0.55;   // fills the pauses too
      const y = h / 2 + Math.sin(x * 0.9 + phase * 3) * amp + noise;
      x === 0 ? ctx.moveTo(x * 2, y) : ctx.lineTo(x * 2, y);
    }
    ctx.stroke();
    const sc = spec.current;
    if (sc) { const { ctx: c2, w: w2, h: h2 } = fit(sc); c2.fillStyle = BAR_OFF; c2.fillRect(0, h2 - 1, w2, 1); }
  }, [conds]);

  const drawLive = useCallback(() => {
    const A = audio.current, cv = wave.current, sc = spec.current; if (!A || !cv || !sc) return;
    const { ctx, w, h } = fit(cv);
    const td = new Float32Array(A.an.fftSize); A.an.getFloatTimeDomainData(td);
    ctx.strokeStyle = INK; ctx.lineWidth = 1.5; ctx.beginPath();
    for (let x = 0; x < w; x++) {
      const v = td[Math.floor((x / w) * td.length)];
      const y = h / 2 - v * (h / 2 - 4) * 1.6;
      x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
    const { ctx: c2, w: w2, h: h2 } = fit(sc);
    const fd = new Uint8Array(A.an.frequencyBinCount); A.an.getByteFrequencyData(fd);
    const bars = 48, nyq = A.ctx.sampleRate / 2, fmax = 8000;
    for (let i = 0; i < bars; i++) {
      const f0 = 60 * Math.pow(fmax / 60, i / bars), f1 = 60 * Math.pow(fmax / 60, (i + 1) / bars);
      let m = 0; for (let k = Math.floor((f0 / nyq) * fd.length); k <= Math.ceil((f1 / nyq) * fd.length); k++) m = Math.max(m, fd[k] ?? 0);
      const bh = (m / 255) * h2;
      c2.fillStyle = f0 > 3400 ? BAR_OFF : BAR; c2.fillRect((i / bars) * w2, h2 - bh, w2 / bars - 2, Math.max(1, bh));
    }
    c2.fillStyle = LINE; c2.fillRect((Math.log(3400 / 60) / Math.log(fmax / 60)) * w2, 0, 1, h2);   // the phone band edge
  }, []);

  // idle loop (ambient), scroll-reactive over the first screen; static under reduced motion
  useEffect(() => {
    if (playing) return;
    const onScroll = () => { scrollP.current = Math.min(1, Math.max(0, window.scrollY / window.innerHeight)); };
    onScroll(); window.addEventListener("scroll", onScroll, { passive: true });
    if (reducedMotion()) { scrollP.current = 0; drawIdle(0); return () => window.removeEventListener("scroll", onScroll); }
    let raf = 0, phase = 0, visible = true;
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    if (wave.current) io.observe(wave.current);
    const loop = () => { if (visible) { phase += 0.03; drawIdle(phase); } raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return () => { cancelAnimationFrame(raf); io.disconnect(); window.removeEventListener("scroll", onScroll); };
  }, [playing, drawIdle]);

  // live loop
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    const loop = () => {
      const A = audio.current; if (!A) return;
      drawLive();
      const now = A.ctx.currentTime - A.t0;
      setT(now);
      if (now > live.duration_s + 0.3) { stop(); return; }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [playing]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ---- audio ----------------------------------------------------------------------------------------------
  const stop = useCallback(() => {
    audio.current?.srcs.forEach((x) => { try { x.stop(); } catch { /* already stopped */ } });
    setPlaying(false);
  }, []);

  const play = useCallback(async () => {
    if (playing) { stop(); return; }
    if (!audio.current) {
      const ctx = new AudioContext();
      const an = ctx.createAnalyser(); an.fftSize = 2048; an.smoothingTimeConstant = 0.6; an.minDecibels = -95; an.maxDecibels = -25; an.connect(ctx.destination);
      const bufs: Record<string, AudioBuffer> = {}, gains: Record<string, GainNode> = {};
      await Promise.all(conds.map(async (c) => {           // lazy: fetched on first play only
        const r = await fetch(asset(c.audio));
        bufs[c.id] = await ctx.decodeAudioData(await r.arrayBuffer());
        const g = ctx.createGain(); g.gain.value = 0; g.connect(an); gains[c.id] = g;
      }));
      audio.current = { ctx, an, bufs, gains, srcs: [], t0: 0 };
    }
    const A = audio.current;
    if (A.ctx.state === "suspended") await A.ctx.resume();
    const t0 = A.ctx.currentTime + 0.05;
    A.srcs = conds.map((c) => { const src = A.ctx.createBufferSource(); src.buffer = A.bufs[c.id]; src.connect(A.gains[c.id]); src.start(t0); return src; });
    conds.forEach((c) => A.gains[c.id].gain.setValueAtTime(c.id === condRef.current ? 1 : 0, t0));
    A.t0 = t0; setT(0); setPlaying(true);
  }, [playing, conds, stop]);

  useEffect(() => { onReady?.(play); }, [onReady, play]);

  const pick = (id: string) => {
    setCond(id);
    const A = audio.current;
    if (A && playing) conds.forEach((c) => A.gains[c.id].gain.setTargetAtTime(c.id === id ? 1 : 0, A.ctx.currentTime, 0.008));
  };

  const current = conds.find((c) => c.id === cond)!;
  return (
    <figure className={s.player} aria-label="Live player: the same call, clean, through a phone line, and under 0 dB market noise">
      <div className={s.top}>
        <div className={s.seg} role="group" aria-label="Condition">
          {conds.map((c) => <button key={c.id} aria-pressed={cond === c.id} onClick={() => pick(c.id)}>{LABEL[c.id] ?? c.id}</button>)}
        </div>
        <button className={s.play} onClick={play} aria-pressed={playing}>{playing ? "Stop" : "▶ Play the call"}</button>
      </div>
      <div className={s.canvasWrap}>
        <canvas ref={wave} className={s.wave} aria-hidden />
        <canvas ref={spec} className={s.spec} aria-hidden />
      </div>
      <figcaption className={s.meta}>
        <span>{playing ? `live: ${LABEL[cond]} · waveform and spectrum (grey above 3.4 kHz)` : "clip " + live.clip + " · synthetic Hinglish call (Gnani Timbre) · switch conditions while it plays"}</span>
        <span>word timing {live.timing}</span>
      </figcaption>
      <div className={s.rows}>
        {current.transcripts.map((tr) => (
          <div key={tr.system} className={s.row}>
            <div className={s.sys}>{tr.label} · {LABEL[cond]}</div>
            <p className={s.words} lang="hi">
              {tr.words.map((w, i) => (
                <span key={i} className={s.w} data-on={t >= tr.t[i]}
                      data-mark={tr.marks[i] ?? undefined}>{w} </span>
              ))}
            </p>
          </div>
        ))}
      </div>
    </figure>
  );
}
