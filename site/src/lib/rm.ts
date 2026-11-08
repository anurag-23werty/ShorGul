/** Tiny, dependency-free so the hero can use it without pulling GSAP into the first chunk. */
export const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
