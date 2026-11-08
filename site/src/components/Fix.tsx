import { useEffect, useMemo, useRef, useState } from "react";
import type { CI, Data, Paired } from "../lib/data";
import { pct, transcript } from "../lib/data";
import { alignWords, morph } from "../lib/align";
import { gsap, reducedMotion, ScrollTrigger, seg } from "../lib/motion";
import s from "./Fix.module.css";

type RepairSys = { id: string; label: string; entity_raw: CI; entity_repaired: CI; delta_entity: Paired; delta_wer_cn: Paired };

export function Fix({ data }: { data: Data }) {
  const ex = data.examples[0];
  const src = transcript(ex, "v25_en", "market_10");      // amounts written as words: fixable
  const stuck = transcript(ex, "whisper", "market_10");   // amounts misheard: not fixable
  const ops = useMemo(() => alignWords(src.text, src.repaired), [src]);
  const reduced = useMemo(reducedMotion, []);
  const [t, setT] = useState(reduced ? 1 : 0);
  const root = useRef<HTMLElement>(null);
  const bars = useRef<HTMLDivElement>(null);
  const sys: RepairSys[] = data.repair.systems;
  const reg = data.repair.regressions;

  useEffect(() => {
    if (reduced) return;
    const st = ScrollTrigger.create({
      trigger: root.current, start: "top 60%", end: "center 40%", scrub: true,
      onUpdate: (self) => setT(Math.round(seg(self.progress, 0, 0.6) * 20) / 20),
    });
    const tl = gsap.timeline({ scrollTrigger: { trigger: bars.current, start: "top 80%", end: "bottom 60%", scrub: true } });
    tl.fromTo(bars.current!.querySelectorAll("[data-grow]"), { scaleX: 0 }, { scaleX: 1, ease: "none", stagger: 0.05 })
      .fromTo(bars.current!.querySelectorAll("[data-ci]"), { opacity: 0 }, { opacity: 1, ease: "none", duration: 0.2 });
    return () => { st.kill(); tl.scrollTrigger?.kill(); tl.kill(); };
  }, [reduced]);

  const words = morph(ops, t);
  const done = t >= 1;
  const changedTo = new Set(ops.filter((o) => o.from !== o.to && o.to).map((o) => o.to!));

  return (
    <section ref={root} className={s.section} aria-labelledby="fix-h">
      <div className={`wrap ${s.grid}`}>
        <div className={s.left}>
          <h2 className={s.h2} id="fix-h">An amount written as words is invisible to a CRM. That part is fixable.</h2>
          <p className={s.p}>
            <code>shorgul.entities.repair</code> rewrites spoken amounts and dates into written form, only when a
            currency word, month or तारीख anchors them. <code>do teen log</code> and <code>kar do</code> stay untouched.
          </p>
          <p className={s.small}>
            0 regressions on {reg.transcripts.toLocaleString("en-IN")} transcripts. The rules were written while reading
            this same benchmark, so the gains below are in-sample; expect less on new calls.
          </p>
        </div>
        <div className={s.right}>
          <div className={s.card}>
            <div className={s.cardHead}>
              <span>Prisma v2.5 · language_code en-IN · clip {ex.clip_id} · market noise</span>
              <span>{done ? "after repair" : "as transcribed"}</span>
            </div>
            <p className={s.text}>
              {words.map((w, i) => {
                const fixed = w.changed && changedTo.has(w.word);
                const spoken = !w.changed && ops.some((o) => o.from === w.word && o.from !== o.to);
                return <span key={i} className={fixed ? s.fixed : spoken ? s.spoken : ""}>{w.word} </span>;
              })}
            </p>
            <div className={s.chips}>
              {src.entities.map((e) => (
                <span key={e.entity} className={s.chip} data-on={done && e.after_repair}>
                  <i>{e.entity.startsWith("₹") ? "amount" : "date"}</i>{done && e.after_repair ? e.entity : e.shown ?? "–"}
                </span>
              ))}
            </div>
            <p className={s.stuck}>
              Repair can't hear for you: Whisper's <span lang="hi">{stuck.entities[0]?.shown ?? "–"}</span> on the
              same call stays broken, because the digits were never recognised.
            </p>
          </div>

          <div className={s.bars} ref={bars}>
            {sys.map((x) => {
              const d = x.delta_entity!;
              const L = (v: number | null) => `${((v ?? 0) * 100).toFixed(1)}%`;
              return (
                <div key={x.id} className={s.barRow}>
                  <span className={s.barLabel}>{x.label}</span>
                  <div className={s.track} aria-label={`${x.label}: ${pct(x.entity_raw.value, 1)} before, ${pct(x.entity_repaired.value, 1)} after repair`}>
                    <span data-grow className={s.before} style={{ width: L(x.entity_raw.value) }} />
                    <span data-grow className={s.after} style={{ width: L(x.entity_repaired.value) }} />
                    <span data-ci className={s.whisker} style={{ left: L(x.entity_repaired.lo), width: `calc(${L(x.entity_repaired.hi)} - ${L(x.entity_repaired.lo)})` }} />
                  </div>
                  <span className={s.delta}>
                    <span className={d.significant ? s.sig : ""}>{d.diff >= 0 ? "+" : ""}{(d.diff * 100).toFixed(1)} pts</span>
                    <small>[{(d.lo * 100).toFixed(1)}, {(d.hi * 100).toFixed(1)}] {d.significant ? "significant" : "not significant"}</small>
                  </span>
                </div>
              );
            })}
            <div className={s.legend}>
              <span><i style={{ background: "var(--ink-3)" }} />as transcribed</span>
              <span><i style={{ background: "var(--accent)" }} />after repair (whisker: 95% CI)</span>
              <span>Hinglish, all conditions pooled</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
