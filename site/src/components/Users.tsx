import type { Data } from "../lib/data";
import { Terminal } from "./Terminal";
import s from "./Users.module.css";

// pull a value out of the real captured output so the copy can never drift from it
const grab = (lines: string[], re: RegExp) => lines.join("\n").match(re)?.[1] ?? "–";

export function Users({ data }: { data: Data }) {
  const t = data.terminals;
  const vb = t.voicebot_golive, sol = t.solutions_deal, gateE = t.release_gate_entity, gateW = t.release_gate_wer;
  const vbGrade = grab(vb.output, /grade (\w)/), solGrade = grab(sol.output, /grade (\w)/);
  const solBreak = grab(sol.output, /breaks at (\w+)/);
  return (
    <section className={s.section} aria-labelledby="users-h">
      <div className="wrap">
        <h2 className={s.h2} id="users-h">Three jobs, three commands. No reference transcripts needed for the first two.</h2>

        <article className={s.story}>
          <div className={s.copy}>
            <div className={s.who}>voice-bot team · before go-live</div>
            <h3 className={s.h3}>Grade the bot's audio before customers call it.</h3>
            <p className={s.p}>
              Point it at a folder of calls. Each one is replayed through a phone line, packet loss, traffic and 0 dB
              market noise, and graded on how much the transcript moves. This Hinglish set gets <b>grade {vbGrade}</b>,
              and every amount and date survives.
            </p>
          </div>
          <div className={s.termCol}><Terminal title="~/collections-bot" runs={[vb]} /></div>
        </article>

        <article className={s.story}>
          <div className={s.copy}>
            <div className={s.who}>solutions engineer · in a deal</div>
            <h3 className={s.h3}>A prospect sends 25 Hindi calls. Show them where it bends.</h3>
            <p className={s.p}>
              Same command, their audio. <b>Grade {solGrade}</b>, breaking point <b>{solBreak.replace("_", " ")}</b>: a
              concrete answer to "will it work in our stores?", with a report.html to send back.
            </p>
          </div>
          <div className={s.termCol}><Terminal title="~/prospect" runs={[sol]} /></div>
        </article>

        <article className={s.story}>
          <div className={s.copy}>
            <div className={s.who}>ML team · release gate</div>
            <h3 className={s.h3}>Gate the release on what customers feel.</h3>
            <p className={s.p}>
              Swapping v2.5 for v3.0 passes on amounts and dates, and fails on read-speech WER in Hindi, Bengali and
              Tamil. A paired bootstrap decides, so a noisy wobble never blocks a build. Exit code 1 stops the pipeline.
            </p>
          </div>
          <div className={s.termCol}><Terminal title="ci / shorgul-gate" runs={[gateE, gateW]} /></div>
        </article>
      </div>
    </section>
  );
}
