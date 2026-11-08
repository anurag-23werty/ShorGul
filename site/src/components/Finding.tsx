import { useEffect, useRef } from "react";
import type { CI, Data } from "../lib/data";
import { ciText, pct } from "../lib/data";
import { gsap, reducedMotion } from "../lib/motion";
import s from "./Finding.module.css";

type Sys = { id: string; label: string; wer: CI; wer_cn: CI; entity: CI; wer_rank: number; entity_rank: number };
type Pair = { a: string; b: string; metric: string; significant: boolean };
const ROW = 76;

function Bar({ c, max }: { c: CI; max: number }) {
  const x = (v: number | null) => `${Math.min(100, ((v ?? 0) / max) * 100)}%`;
  return (
    <div className={s.bar} aria-hidden>
      <span className={s.ciBar} style={{ left: x(c.lo), width: `calc(${x(c.hi)} - ${x(c.lo)})` }} />
      <span className={s.point} style={{ left: x(c.value) }} />
    </div>
  );
}

export function Finding({ data }: { data: Data }) {
  const systems: Sys[] = data.rankings.systems;
  const pairs: Pair[] = data.rankings.pairs;
  const byWer = [...systems].sort((a, b) => a.wer_rank - b.wer_rank);
  const byEnt = [...systems].sort((a, b) => a.entity_rank - b.entity_rank);
  const maxWer = Math.max(...systems.map((x) => x.wer.hi ?? 0));
  const sig = (a: string, b: string, m: string) =>
    pairs.find((p) => ((p.a === a && p.b === b) || (p.a === b && p.b === a)) && p.metric === m)?.significant;
  const crosses = (x: Sys) =>
    systems.some((y) => y.id !== x.id && Math.sign(x.wer_rank - y.wer_rank) !== Math.sign(x.entity_rank - y.entity_rank));
  const svgRef = useRef<SVGSVGElement>(null);
  const root = useRef<HTMLElement>(null);

  // lines draw with scroll: the crossing IS the finding
  useEffect(() => {
    const paths = svgRef.current?.querySelectorAll("path");
    if (!paths?.length) return;
    paths.forEach((p) => { const L = p.getTotalLength(); p.style.strokeDasharray = `${L}`; p.style.strokeDashoffset = reducedMotion() ? "0" : `${L}`; });
    if (reducedMotion()) return;
    const tw = gsap.to(paths, { strokeDashoffset: 0, ease: "none", stagger: 0.08,
      scrollTrigger: { trigger: root.current, start: "top 55%", end: "center 45%", scrub: true } });
    return () => { tw.scrollTrigger?.kill(); tw.kill(); };
  }, []);

  const h = data.headline;
  const m = h.matched_v30_minus_v25;
  const v25hi = systems.find((x) => x.id === "v25_hi")!;
  const en = systems.find((x) => x.id === "v25_en")!, wh = systems.find((x) => x.id === "whisper")!;
  const tieW = (a: Sys, b: Sys) => sig(a.id, b.id, "wer") === false;
  const tieE = (a: Sys, b: Sys) => sig(a.id, b.id, "entity") === false;

  return (
    <section ref={root} className={s.section} aria-labelledby="finding-h">
      <div className={`wrap ${s.grid}`}>
        <div className={s.left}>
          <h2 className={s.h2} id="finding-h">Rank by WER, then by the money. The order changes.</h2>
          <p className={s.p}>
            Same 25 calls, same audio, all 8 conditions. WER puts {v25hi.label} first. That lead is the ₹ vs रुपये
            spelling: count the currency word the same way and it is <b>a tie</b>{" "}
            <span className={s.ci}>({(m.wer_cn!.diff * 100).toFixed(1)} pts {ciText({ value: 0, lo: m.wer_cn!.lo, hi: m.wer_cn!.hi }, 1)})</span>,
            and so are the amounts.
          </p>
          <p className={s.p}>
            WER can't separate {wh.label} from {en.label} <span className={s.ci}>(tie)</span>. The money separates them by{" "}
            <span className={s.num}>{((wh.entity.value! - en.entity.value!) * 100).toFixed(0)} points</span>.
          </p>
          <div className={s.callout}>
            <div className={s.calloutBig}>
              {pct(en.entity.value)} <span aria-hidden>→</span> <span className={s.to}>{pct(v25hi.entity.value, 1)}</span>
            </div>
            <div className={s.calloutSmall}>Prisma v2.5, same audio, one setting: language_code en-IN → hi-IN.</div>
          </div>
        </div>
        <div className={s.right}>
          <div className={s.board}>
            <div className={s.colHead}>by WER (lower is better)</div>
            <div className={s.colHead} />
            <div className={`${s.colHead} ${s.r}`}>by amount & date accuracy</div>
            <div className={s.rows}>
              {byWer.map((x, i) => (
                <div key={x.id} className={s.item}>
                  <div className={s.itemTop}>
                    <span className={s.rank}>{i + 1}</span><span className={s.label}>{x.label}</span>
                    <span className={s.val}>{pct(x.wer.value, 1)}</span>
                  </div>
                  <Bar c={x.wer} max={maxWer} />
                  {i > 0 && tieW(byWer[i - 1], x) && <span className={s.tie}>tie with #{i}</span>}
                </div>
              ))}
            </div>
            <svg ref={svgRef} className={s.svg} viewBox={`0 0 100 ${ROW * 4}`} preserveAspectRatio="none" aria-hidden>
              {systems.map((x) => {
                const y1 = (x.wer_rank - 0.5) * ROW, y2 = (x.entity_rank - 0.5) * ROW;
                return <path key={x.id} className={`${s.line} ${crosses(x) ? s.lineCross : ""}`}
                             d={`M0,${y1} C50,${y1} 50,${y2} 100,${y2}`} vectorEffect="non-scaling-stroke" />;
              })}
            </svg>
            <div className={`${s.rows} ${s.entity}`}>
              {byEnt.map((x, i) => (
                <div key={x.id} className={s.item}>
                  <div className={s.itemTop}>
                    <span className={s.rank}>{i + 1}</span><span className={s.label}>{x.label}</span>
                    <span className={s.val}>{pct(x.entity.value, 1)}</span>
                  </div>
                  <Bar c={x.entity} max={1} />
                  {i > 0 && tieE(byEnt[i - 1], x) && <span className={s.tie}>tie with #{i}</span>}
                </div>
              ))}
            </div>
          </div>
          <p className={s.legend}>
            Thin bars: 95% bootstrap CI over clips. "Tie" means a paired test can't tell the two apart. Hinglish
            call-centre lines (25, synthetic speech), pooled over all conditions.
          </p>
        </div>
      </div>
    </section>
  );
}
