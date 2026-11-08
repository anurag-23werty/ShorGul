import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger);

export const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let lenis: Lenis | null = null;

/** Smooth scroll that drives ScrollTrigger. Skipped entirely under reduced motion. */
export function startSmoothScroll(): () => void {
  if (reducedMotion()) return () => {};
  lenis = new Lenis({ duration: 1.05, smoothWheel: true });
  lenis.on("scroll", ScrollTrigger.update);
  const tick = (time: number) => lenis?.raf(time * 1000);
  gsap.ticker.add(tick);
  gsap.ticker.lagSmoothing(0);
  return () => {
    gsap.ticker.remove(tick);
    lenis?.destroy();
    lenis = null;
  };
}

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
/** progress of x inside [a, b] */
export const seg = (x: number, a: number, b: number) => clamp01((x - a) / (b - a));
export { gsap, ScrollTrigger };
