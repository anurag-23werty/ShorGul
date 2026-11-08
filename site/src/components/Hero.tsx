import { useRef } from "react";
import type { Data } from "../lib/data";
import { ciText, pct } from "../lib/data";
import s from "./Hero.module.css";
import headline from "../generated/headline.json";
import { LivePlayer } from "./LivePlayer";

const REPO = "https://github.com/anurag-23werty/ShorGul";
export function Hero({ data }: { data: Data | null }) {
  const h = headline as Data["headline"];
  const playRef = useRef<(() => void) | null>(null);
  const hear = () => { playRef.current?.(); document.getElementById("live")?.scrollIntoView({ behavior: "smooth", block: "center" }); };

  return (
    <header className={s.hero}>
      <div className="wrap">
        <nav className={s.brand} aria-label="Primary">
          <a className={s.logo} href="#top">shorgul <b>/ शोर-गुल</b></a>
          <div className={s.navlinks}>
            <a href="#method">Method</a>
            <a href={REPO}>GitHub</a>
          </div>
        </nav>
        <h1 className={s.h1} id="top">WER picks the wrong model for Indian phone calls.</h1>
        <p className={s.sub}>
          On the same customer-care audio, one API setting moved payment-amount accuracy from{" "}
          <span className={s.num}>{pct(h.entity_v25_en.value)}</span> to{" "}
          <span className={s.num}>{pct(h.entity_v25_hi.value, 1)}</span>{" "}
          <span className={s.ci}>{ciText(h.entity_v25_hi, 1)}</span>. And between the two well-configured
          models, WER ranks them by how they write ₹, not by whether they heard it.{" "}
          <strong>ShorGul tests the setting, the call and the money.</strong>
        </p>
        <div className={s.actions}>
          <button className={`${s.btn} ${s.primary}`} onClick={hear}>
            <span className={s.dot} aria-hidden /> Hear the difference
          </button>
          <a className={s.btn} href={REPO}>GitHub</a>
        </div>
        <div id="live" className={s.live}>{data && <LivePlayer data={data} onReady={(p) => { playRef.current = p; }} />}</div>
      </div>
    </header>
  );
}
