import type { Data } from "../lib/data";
import { asset, pct, transcript } from "../lib/data";
import { Carousel } from "./Carousel";
import { CountUp, TypeCmd } from "./Live";
import s from "./Carousels.module.css";
import { useClip } from "./useClip";
import { wavePath } from "./wave";

type CondCard = { id: string; label: string; desc: string; audio: string; peaks: number[];
  wer: Record<string, { value: number; lo: number; hi: number; vs_clean: { diff: number; significant: boolean } | null }> };
type Finding = { finding: string; big: string; rest: string; test: string };
const ciTxt = (lo: number, hi: number) => `[${(lo * 100).toFixed(1)}, ${(hi * 100).toFixed(1)}]`;

export function ConditionsCarousel({ data }: { data: Data }) {
  const { play, stop, playing } = useClip();
  const cards: CondCard[] = data.conditions.cards;
  const max = Math.max(...cards.flatMap((c) => c.peaks));
  const slides = cards.map((c) => (
    <article key={c.id} className={s.card}>
      <div className={s.kicker}>{c.id}</div>
      <h3 className={s.title}>{c.label}</h3>
      <p className={s.desc}>{c.desc}</p>
      <svg className={s.wave} viewBox="0 0 300 44" preserveAspectRatio="none" aria-hidden>
        <path d={wavePath(c.peaks.map((p) => p / max), 300, 44, 1)} />
      </svg>
      <button className={s.play} aria-pressed={playing === c.id}
              onClick={() => (playing === c.id ? stop() : play(c.id, asset(c.audio)))}>
        {playing === c.id ? "■ stop" : "▶ play this condition"}
      </button>
      <div className={s.stats}>
        {(["prisma-v2.5", "prisma-v3.0"] as const).map((m) => {
          const w = c.wer[m];
          const vc = w.vs_clean;
          return (
            <div key={m}>
              <div className={s.stat}>
                <span>{m.replace("prisma-", "Prisma ")}</span>
                <span><b>{pct(w.value, 1)}</b> <small>{ciTxt(w.lo, w.hi)}</small></span>
              </div>
              {vc && <div className={`${s.verdict} ${vc.significant ? s.sig : ""}`}>
                {vc.diff >= 0 ? "+" : ""}{(vc.diff * 100).toFixed(1)} pts vs clean · {vc.significant ? "significant" : "no significant change"}
              </div>}
            </div>
          );
        })}
      </div>
    </article>
  ));
  return (
    <section className={s.section} aria-labelledby="cond-h">
      <div className="wrap">
        <Carousel label="Conditions" slides={slides} slideWidth={{ lg: "30%", md: "48%", sm: "86%" }}
          heading={<>
            <h2 className={s.h2} id="cond-h">Seven ways a call goes wrong. Listen to each.</h2>
            <p className={s.sub}>One Hindi FLEURS clip ({data.conditions.clip}) rendered through every condition. WER is over
              all 25 Hindi clips, 95% CI, with the paired test against clean.</p>
          </>} />
      </div>
    </section>
  );
}

export function FindingsCarousel({ data }: { data: Data }) {
  const rows: Finding[] = data.findings;
  const slides = rows.map((f, i) => (
    <article key={i} className={s.card}>
      <div className={s.big}><CountUp text={f.big} /></div>
      <p className={s.findingText}>{f.finding}</p>
      <p className={s.rest}><CountUp text="" after={f.rest} ms={1100} /></p>
      <div className={s.test}>{f.test}</div>
    </article>
  ));
  return (
    <section className={s.section} aria-labelledby="findings-h">
      <div className="wrap">
        <Carousel label="Findings" slides={slides} slideWidth={{ lg: "32%", md: "50%", sm: "86%" }}
          heading={<>
            <h2 className={s.h2} id="findings-h">Everything measured, one card each.</h2>
            <p className={s.sub}>The same rows as the README's findings table, generated from the results files.</p>
          </>} />
      </div>
    </section>
  );
}

function AuditPreview({ table, grade }: { table: { condition: string; stability: number; grade: string }[]; grade: string }) {
  const max = Math.max(0.05, ...table.map((r) => r.stability));
  return (
    <div className={s.preview}>
      <div className={s.stat}><span>report.html</span><span className={s.grade}>{grade}</span></div>
      {table.map((r) => (
        <div key={r.condition} className={s.gradeRow}>
          <span>{r.condition}</span>
          <span className={s.track}><span className={s.fill} style={{ display: "block", width: `${(r.stability / max) * 100}%` }} /></span>
          <span>{r.grade}</span>
        </div>
      ))}
    </div>
  );
}

export function UsersCarousel({ data }: { data: Data }) {
  const t = data.terminals;
  const g = (lines: string[], re: RegExp) => lines.join("\n").match(re)?.[1] ?? "–";
  const ex = data.examples[0];
  const before = transcript(ex, "v25_en", "market_10");
  const lastLine = (lines: string[]) => lines[lines.length - 1] ?? "";
  const slides = [
    <article key="vb" className={s.card}>
      <div className={s.kicker}>voice-bot team · before go-live</div>
      <h3 className={s.title}>Grade the bot's audio before customers call it.</h3>
      <p className={s.desc}>No reference transcripts. Each call is replayed through a phone line, packet loss, traffic and 0 dB market noise.</p>
      <TypeCmd className={s.cmd} cmd={t.voicebot_golive.command} />
      <AuditPreview table={t.voicebot_golive.table} grade={g(t.voicebot_golive.output, /grade (\w)/)} />
    </article>,
    <article key="se" className={s.card}>
      <div className={s.kicker}>solutions engineer · in a deal</div>
      <h3 className={s.title}>Run the prospect's calls, send back one report.</h3>
      <p className={s.desc}>A grade, the breaking point ({g(t.solutions_deal.output, /breaks at (\w+)/).replace("_", " ")}) and the worst calls, in one self-contained HTML file.</p>
      <TypeCmd className={s.cmd} cmd={t.solutions_deal.command} />
      <AuditPreview table={t.solutions_deal.table} grade={g(t.solutions_deal.output, /grade (\w)/)} />
    </article>,
    <article key="ml" className={s.card}>
      <div className={s.kicker}>ML team · release gate</div>
      <h3 className={s.title}>Fail CI only on a significant regression.</h3>
      <p className={s.desc}>Paired bootstrap on the same clips; exit code 1 stops the pipeline.</p>
      <TypeCmd className={s.cmd} cmd={t.release_gate_entity.command} />
      <div className={s.preview}>
        <span className={s.pass}>{lastLine(t.release_gate_entity.output)}</span>
        <span className={s.fail}>{lastLine(t.release_gate_wer.output)}</span>
        <span className={s.kicker}>same v2.5 → v3.0 swap: passes on amounts, fails on read-speech WER</span>
      </div>
    </article>,
    <article key="rp" className={s.card}>
      <div className={s.kicker}>anyone storing money in transcripts</div>
      <h3 className={s.title}>Turn spoken amounts into numbers a CRM can read.</h3>
      <p className={s.desc}>Model-agnostic and anchored: "do teen log" and "kar do" stay untouched.</p>
      <TypeCmd className={s.cmd} prompt=">>> " cmd={`repair("${before.entities[0]?.shown ?? ""}")`} />
      <div className={s.preview}>
        <div className={s.snippet}><s>{before.text}</s></div>
        <div className={s.snippet}>{before.repaired.split(/(₹[\d,]+|\b\d+\b)/).map((p, i) => (/^(₹[\d,]+|\d+)$/.test(p) ? <mark key={i}>{p}</mark> : p))}</div>
      </div>
    </article>,
  ];
  return (
    <section className={s.section} aria-labelledby="users-h">
      <div className="wrap">
        <Carousel label="Who uses it" slides={slides} slideWidth={{ lg: "45%", md: "70%", sm: "90%" }}
          heading={<h2 className={s.h2} id="users-h">Four jobs, one tool.</h2>} />
      </div>
    </section>
  );
}
