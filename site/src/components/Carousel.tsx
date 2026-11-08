import useEmblaCarousel from "embla-carousel-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { reducedMotion } from "../lib/motion";
import s from "./Carousel.module.css";

type Props = {
  label: string;
  heading?: ReactNode;
  slides: ReactNode[];
  slideWidth?: { lg?: string; md?: string; sm?: string };
  onSelect?: (index: number) => void;
};

/** Accessible horizontal carousel: snap, drag/swipe, arrows, dots, progress, keyboard. No autoplay. */
export function Carousel({ label, heading, slides, slideWidth, onSelect }: Props) {
  const [viewport, api] = useEmblaCarousel({
    align: "start", containScroll: "trimSnaps", dragFree: false, duration: reducedMotion() ? 1 : 26,
  });
  const [selected, setSelected] = useState(0);
  const [snaps, setSnaps] = useState<number[]>([]);
  const [canPrev, setCanPrev] = useState(false);
  const [canNext, setCanNext] = useState(true);
  const bar = useRef<HTMLDivElement>(null);

  const sync = useCallback(() => {
    if (!api) return;
    setSelected(api.selectedScrollSnap());
    setCanPrev(api.canScrollPrev());
    setCanNext(api.canScrollNext());
    onSelect?.(api.selectedScrollSnap());
  }, [api, onSelect]);

  useEffect(() => {
    if (!api) return;
    const progress = () => {
      const p = Math.max(0, Math.min(1, api.scrollProgress()));
      if (bar.current) bar.current.style.transform = `scaleX(${snaps.length <= 1 ? 1 : Math.max(p, 0.04)})`;
    };
    setSnaps(api.scrollSnapList());
    sync(); progress();
    api.on("select", sync).on("reInit", () => { setSnaps(api.scrollSnapList()); sync(); }).on("scroll", progress);
    return () => { api.off("select", sync).off("scroll", progress); };
  }, [api, sync, snaps.length]);

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowRight") { e.preventDefault(); api?.scrollNext(); }
    if (e.key === "ArrowLeft") { e.preventDefault(); api?.scrollPrev(); }
  };
  const style = {
    "--slide": slideWidth?.lg ?? "40%", "--slide-md": slideWidth?.md ?? "70%", "--slide-sm": slideWidth?.sm ?? "88%",
  } as React.CSSProperties;

  return (
    <div className={s.root} role="region" aria-roledescription="carousel" aria-label={label} style={style}>
      <div className={s.head}>
        <div>{heading}</div>
        <div className={s.controls}>
          <button className={s.arrow} onClick={() => api?.scrollPrev()} disabled={!canPrev} aria-label="Previous slide">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M10 3 5 8l5 5" /></svg>
          </button>
          <button className={s.arrow} onClick={() => api?.scrollNext()} disabled={!canNext} aria-label="Next slide">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="m6 3 5 5-5 5" /></svg>
          </button>
        </div>
      </div>
      <div className={s.viewport} ref={viewport} tabIndex={0} onKeyDown={onKey}
           aria-label={`${label}: use left and right arrow keys`}>
        <div className={s.track}>
          {slides.map((node, i) => (
            <div key={i} className={s.slide} role="group" aria-roledescription="slide"
                 aria-label={`${i + 1} of ${slides.length}`}>{node}</div>
          ))}
        </div>
      </div>
      <div className={s.foot}>
        <div className={s.progress} aria-hidden><div ref={bar} className={s.bar} /></div>
        <div className={s.dots}>
          {snaps.map((_, i) => (
            <button key={i} className={s.dot} aria-label={`Go to slide ${i + 1}`} aria-current={i === selected}
                    onClick={() => api?.scrollTo(i)} />
          ))}
        </div>
        <span className="sr-only" aria-live="polite">Slide {selected + 1} of {snaps.length || slides.length}</span>
      </div>
    </div>
  );
}
