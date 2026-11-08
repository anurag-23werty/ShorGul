import { useEffect } from "react";
import { CallScene } from "./components/CallScene";
import { ConditionsCarousel, FindingsCarousel, UsersCarousel } from "./components/Carousels";
import { Close } from "./components/Close";
import { Curves } from "./components/Curves";
import { Finding } from "./components/Finding";
import { Fix } from "./components/Fix";
import { Pipeline } from "./components/Pipeline";
import type { Data } from "./lib/data";
import { ScrollTrigger, startSmoothScroll } from "./lib/motion";

/** Everything below the hero, loaded as its own chunk (GSAP, Lenis, Embla live here). */
export default function Rest({ data }: { data: Data }) {
  useEffect(() => {
    const stop = startSmoothScroll();
    requestAnimationFrame(() => ScrollTrigger.refresh());
    return stop;
  }, []);
  return (
    <>
      <main>
        <CallScene data={data} />
        <ConditionsCarousel data={data} />
        <Finding data={data} />
        <Fix data={data} />
        <Curves data={data} />
        <FindingsCarousel data={data} />
        <UsersCarousel data={data} />
        <Pipeline data={data} />
      </main>
      <Close data={data} />
    </>
  );
}
