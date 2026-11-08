import { useEffect, useRef, useState } from "react";
import type { Data } from "../lib/data";
import { asset, ciText, pct } from "../lib/data";
import s from "./Hero.module.css";
import { useClip } from "./useClip";
import { wavePath } from "./wave";

const REPO = "https://github.com/anurag-23werty/ShorGul";
const W = 1000, H = 120;

export function Hero({ data }: { data: Data }) {
  const ex = data.examples[0];
  const h = data.headline;
  const { play, stop, playing, progress } = useClip();
  const [which, setWhich] = useState<"clean" | "market_10">("clean");
  const head = useRef<SVGLineElement>(null);

  // playhead follows the real audio position (explains which moment you are hearing)
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    const step = () => {
      head.current?.setAttribute("transform", `translate(${(progress.current * W).toFixed(1)},0)`);
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [playing, progress]);

  const hear = () => {
    if (playing) { stop(); setWhich("clean"); return; }
    setWhich("clean");
    play("clean", asset(ex.audio.clean), () => {
      setWhich("market_10");
      play("market_10", asset(ex.audio.market_10), () => setWhich("clean"));
    });
  };

  const label = which === "clean" ? "clean recording" : "same call · market noise at 10 dB through a phone line";

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
          <button className={`${s.btn} ${s.primary}`} onClick={hear} aria-pressed={!!playing}>
            <span className={s.dot} aria-hidden /> {playing ? "Stop" : "Hear the difference"}
          </button>
          <a className={s.btn} href={REPO}>GitHub</a>
        </div>
        <figure className={`${s.wave} ${playing ? s.playing : ""}`} aria-label="Waveform of the example call">
          <svg className={s.waveSvg} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img"
               aria-label={`Waveform, ${label}`}>
            <path className={s.wavePath} d={wavePath(ex.waveform[which], W, H, 1.6)} />
            <line ref={head} className={s.playhead} x1={0} x2={0} y1={0} y2={H} />
          </svg>
          <figcaption className={s.caption}>
            <span>clip {ex.clip_id} · {ex.duration_s.toFixed(1)} s · real benchmark audio</span>
            <span className={s.state}>{playing ? `playing: ${label}` : label}</span>
          </figcaption>
        </figure>
      </div>
    </header>
  );
}
