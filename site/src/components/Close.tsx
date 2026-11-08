import type { Data } from "../lib/data";
import { pct } from "../lib/data";
import s from "./Close.module.css";

const REPO = "https://github.com/anurag-23werty/ShorGul";
const FINDING = `${REPO}/blob/main/results/finding_check.md`;
const DASHBOARD = "https://shorgul.streamlit.app/";
const ME = { name: "Anurag Choudhury", github: "https://github.com/anurag-23werty", linkedin: "https://www.linkedin.com/in/anurag-choudhury-ai/" };

export function Close({ data }: { data: Data }) {
  const p = data.pipeline;
  const per = Math.round(p.clips / p.languages.length);
  const v = data.validation;
  const rc25 = v.real_calls.find((r: { model: string }) => r.model === "Prisma v2.5");
  const heldRep = v.heldout.find((x: { system: string }) => x.system.includes("en-IN")).held_rep;
  return (
    <footer className={s.close}>
      <div className="wrap">
        <p className={s.big}>Built on Gnani Prisma v2.5, v3.0 and Timbre.</p>
        <div className={s.links}>
          <a className={`${s.btn} ${s.primary}`} href={REPO}>Code and results on GitHub</a>
          <a className={s.btn} href={FINDING}>How the finding was checked</a>
        </div>

        <section className={s.method} id="method" aria-labelledby="method-h">
          <div className={s.methodHead}>
            <h2 id="method-h">Method & limitations</h2>
            <p>What the numbers on this page are, and what they are not.</p>
          </div>
          <div className={s.methodBody}>
            <dl className={s.dl}>
              <dt>data</dt><dd>{p.clips} clips: {per} each of Hindi, Bengali and Tamil from Google FLEURS, and {per} Hinglish customer-care lines voiced with Gnani Timbre.</dd>
              <dt>conditions</dt><dd>Noise mixed at the caller (DEMAND street traffic and public square) at an acoustic SNR, then a 300–3400 Hz band-pass, 8 kHz μ-law and 5% packet loss; plus Opus 8 kbps VoIP and AMR-NB 12.2 kbps mobile. Seeded per clip and condition.</dd>
              <dt>metrics</dt><dd>Corpus WER and CER after Indic normalisation. Currency-neutral WER scores ₹4,500 and 4,500 रुपये the same. Amount & date accuracy = share of reference amounts and dates written correctly.</dd>
              <dt>statistics</dt><dd>{data.ci}. "Significant" means the interval excludes zero.</dd>
            </dl>
            <ul className={s.limits}>
              <li><b>{per} clips per language.</b> Many differences are honestly reported as ties.</li>
              <li><b>Hinglish is synthetic speech.</b> Real speech is covered by {v.real_calls_n} Gram Vaani phone calls: Hindi
                community-radio callers (Prisma v2.5 WER {pct(rc25.all[0], 1)} on real calls vs {pct(rc25.fleurs_phone_sim[0], 1)} on
                simulated phone read speech), not Hinglish customer care.</li>
              <li><b>Simulated packet loss is optimistic.</b> Real networks conceal lost packets instead of leaving silence, and
                our dropout detector fails on real calls.</li>
              <li><b>Entity repair, measured out of sample:</b> {pct(heldRep[0])} [{pct(heldRep[1])}, {pct(heldRep[2])}] on{" "}
                {v.heldout_lines} lines written before any audio existed, vs 100% on the lines it was built on.</li>
              <li><b>The en-IN config came from the original project spec</b>, kept on purpose as the example of a default-style setting.</li>
            </ul>
          </div>
        </section>

        <div className={s.foot}>
          <div className={s.me}>
            <span>Built on Gnani Prisma &amp; Timbre</span>
            <a href={REPO}>GitHub</a>
            <a href={DASHBOARD}>Dashboard</a>
          </div>
          <div className={s.me}>
            <strong>{ME.name}</strong>
            <a href={ME.github}>GitHub</a>
            <a href={ME.linkedin}>LinkedIn</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
