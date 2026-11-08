import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { reducedMotion } from "../lib/motion";

/** Fires once when the element is actually visible (respects carousel clipping, unlike scroll position). */
function useSeen<T extends Element>(threshold = 0.6) {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(reducedMotion());
  useEffect(() => {
    if (seen || !ref.current) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [seen, threshold]);
  return [ref, seen] as const;
}

/** Counts the first number inside `text` up from zero (keeping sign, decimals, commas), then reveals `after`
 *  (the confidence interval), so the point estimate lands first and its uncertainty right behind it. */
export function CountUp({ text, after, className, ms = 1100 }: { text: string; after?: ReactNode; className?: string; ms?: number }) {
  const [ref, seen] = useSeen<HTMLSpanElement>();
  const m = text.match(/([+-−]?)(\d[\d,]*)(\.\d+)?/);
  const target = m ? parseFloat((m[2] + (m[3] ?? "")).replace(/,/g, "")) : 0;
  const dec = m?.[3] ? m[3].length - 1 : 0;
  const [v, setV] = useState(reducedMotion() || !m ? target : 0);
  const [done, setDone] = useState(reducedMotion());
  useEffect(() => {
    if (!seen || done) return;
    if (!m) { const id = window.setTimeout(() => setDone(true), ms); return () => clearTimeout(id); }   // reveal-only use
    let raf = 0; const t0 = performance.now();
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - p, 3);
      setV(p === 1 ? target : target * e);
      if (p < 1) raf = requestAnimationFrame(step); else setDone(true);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [seen]);   // eslint-disable-line react-hooks/exhaustive-deps
  const shown = m ? text.replace(m[0], m[1] + v.toLocaleString("en-IN", { minimumFractionDigits: dec, maximumFractionDigits: dec })) : text;
  return (
    <>
      <span ref={ref} className={className} aria-label={text}><span aria-hidden>{shown}</span></span>
      {after !== undefined && <span style={{ opacity: done ? 1 : 0, transition: "opacity 400ms ease-out" }}>{after}</span>}
    </>
  );
}

/** Types a real command once its card is visible; the caret blinks only while typing. */
export function TypeCmd({ cmd, prompt = "$ ", className }: { cmd: string; prompt?: string; className?: string }) {
  const [ref, seen] = useSeen<HTMLDivElement>(0.8);
  const [n, setN] = useState(reducedMotion() ? cmd.length : 0);
  useEffect(() => {
    if (!seen || reducedMotion()) return;
    let i = 0, timer = 0;
    const tick = () => { i += 1; setN(i); if (i < cmd.length) timer = window.setTimeout(tick, 16); };
    timer = window.setTimeout(tick, 200);
    return () => clearTimeout(timer);
  }, [seen, cmd]);
  return (
    <div ref={ref} className={className} aria-label={prompt + cmd}>
      <span aria-hidden><span style={{ color: "var(--ink-3)" }}>{prompt}</span>{cmd.slice(0, n)}
        {n < cmd.length && <span style={{ display: "inline-block", width: "0.55em", height: "1em", verticalAlign: "-0.15em", background: "var(--ink-2)" }} />}
      </span>
    </div>
  );
}
