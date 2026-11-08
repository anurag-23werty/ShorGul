import { useEffect, useRef, useState } from "react";
import { reducedMotion, ScrollTrigger } from "../lib/motion";
import s from "./Terminal.module.css";

export type Run = { command: string; output: string[]; exit_code: number };

function lineClass(l: string) {
  if (/\bPASS\b/.test(l)) return s.pass;
  if (/\bFAIL\b|REGRESSION/.test(l)) return s.fail;
  return undefined;
}

/** Types the real command, then prints its real captured output. Starts once, when scrolled into view. */
export function Terminal({ runs, title }: { runs: Run[]; title: string }) {
  const full = runs.map((r) => ({ cmd: r.command, out: r.output, code: r.exit_code }));
  const total = full.reduce((n, r) => n + r.cmd.length + r.out.length, 0);
  const [n, setN] = useState(reducedMotion() ? total : 0);  // progress counter: chars of command, then lines
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (reducedMotion()) return;
    let timer = 0;
    const st = ScrollTrigger.create({
      trigger: root.current, start: "top 75%", once: true,
      onEnter: () => {
        let i = 0;
        const tick = () => {
          i += 1; setN(i);
          if (i < total) {
            // characters type fast; each output line lands like a real process printing
            let acc = 0, inCmd = false;
            for (const r of full) { if (i < acc + r.cmd.length) { inCmd = true; break; } acc += r.cmd.length + r.out.length; }
            timer = window.setTimeout(tick, inCmd ? 14 : 55);
          }
        };
        tick();
      },
    });
    return () => { st.kill(); clearTimeout(timer); };
  }, [total]);

  const nodes: React.ReactNode[] = [];
  let left = n;
  full.forEach((r, k) => {
    if (left <= 0 && k > 0) return;
    const c = Math.min(left, r.cmd.length); left -= c;
    nodes.push(<span key={`c${k}`}><span className={s.prompt}>$ </span><span className={s.cmd}>{r.cmd.slice(0, c)}</span>{left <= 0 && n < total && <span className={s.caret} aria-hidden />}{"\n"}</span>);
    const L = Math.min(left, r.out.length); left -= L;
    r.out.slice(0, L).forEach((l, j) => nodes.push(<span key={`o${k}-${j}`} className={lineClass(l)}>{l}{"\n"}</span>));
    if (L === r.out.length && L > 0) nodes.push(<span key={`x${k}`} className={s.prompt}>{`exit ${r.code}\n`}</span>);
  });

  return (
    <div ref={root} className={s.term}>
      <div className={s.bar}><span>{title}</span><span>real output, from the result cache</span></div>
      <pre className={s.body} aria-label={full.map((r) => `$ ${r.cmd}\n${r.out.join("\n")}`).join("\n")}>{nodes}</pre>
    </div>
  );
}
