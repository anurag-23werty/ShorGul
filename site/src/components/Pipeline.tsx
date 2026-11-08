import { useEffect, useRef } from "react";
import type { Data } from "../lib/data";
import { gsap, reducedMotion } from "../lib/motion";
import s from "./Pipeline.module.css";

export function Pipeline({ data }: { data: Data }) {
  const p = data.pipeline;
  const flow = useRef<HTMLDivElement>(null);
  const conds: string[] = p.conditions;
  const nodes = [
    { title: "Data", big: p.clips, unit: "clips", items: ["FLEURS hi · bn · ta", "Hinglish call-centre lines", "voiced with Gnani Timbre"] },
    { title: "Phone simulation", big: conds.length, unit: "conditions", items: ["300–3400 Hz · 8 kHz μ-law", "5% packet loss", "traffic · market noise", "Opus 8 kbps VoIP"] },
    { title: "Fixes", big: -1, unit: "variants", items: ["denoise (spectral gating)", "context hints (v3.0)", "matched language_code"] },
    { title: "ASR", big: p.models.length, unit: "models", items: ["Gnani Prisma v2.5", "Gnani Prisma v3.0", "Whisper-small (local)", "cached: nothing billed twice"] },
    { title: "Scoring", big: p.paired_tests, unit: "paired tests", items: ["WER · currency-neutral WER", "amount & date accuracy", "bootstrap 95% CIs", "entity repair"] },
  ];
  nodes.forEach((n) => { if (n.big === -1) n.big = n.items.length; });

  // the machine assembles left to right as you read it: one node, then the wire to the next
  useEffect(() => {
    const el = flow.current;
    if (!el || reducedMotion()) return;
    const tl = gsap.timeline({ scrollTrigger: { trigger: el, start: "top 85%", end: "top 35%", scrub: true } });
    el.querySelectorAll<HTMLElement>("[data-node]").forEach((n) => {
      tl.fromTo(n.querySelector("[data-box]"), { opacity: 0, y: 14 }, { opacity: 1, y: 0, ease: "none", duration: 1 });
      const link = n.querySelector("[data-link]");
      if (link) tl.fromTo(link, { scale: 0 }, { scale: 1, ease: "none", duration: 0.5 });
    });
    return () => { tl.scrollTrigger?.kill(); tl.kill(); };
  }, []);

  return (
    <section className={s.section} aria-labelledby="how-h">
      <div className="wrap">
        <h2 className={s.h2} id="how-h">One pipeline, every stage on disk, re-runnable on its own.</h2>
        <p className={s.lede}>
          {p.transcripts.toLocaleString("en-IN")} transcripts, {p.failed} failed. Deterministic degradation (seeded per
          clip and condition), a cache in front of every billed call, and a --max-calls cap that defaults to zero.
        </p>
        <div className={s.flow} ref={flow}>
          {nodes.map((n, i) => (
            <div key={n.title} className={s.node} data-node>
              <div className={s.box} data-box>
                <div className={s.step}>0{i + 1}</div>
                <div className={s.title}>{n.title}</div>
                <ul className={s.list}>{n.items.map((x) => <li key={x}>{x}</li>)}</ul>
                <div className={s.big}>{typeof n.big === "number" ? n.big.toLocaleString("en-IN") : n.big}<small>{n.unit}</small></div>
              </div>
              <span className={s.link} data-link aria-hidden />
            </div>
          ))}
        </div>
        <div className={s.out}>
          <span>ships as</span><span className={s.tag}>shorgul audit</span><span className={s.tag}>shorgul compare</span>
          <span className={s.tag}>dashboard</span><span className={s.tag}>this page</span>
        </div>
      </div>
    </section>
  );
}
