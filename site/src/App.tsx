import { useEffect, useState } from "react";
import { CallScene } from "./components/CallScene";
import { Curves } from "./components/Curves";
import { Finding } from "./components/Finding";
import { Fix } from "./components/Fix";
import { Hero } from "./components/Hero";
import type { Data } from "./lib/data";
import { loadData } from "./lib/data";
import { ScrollTrigger, startSmoothScroll } from "./lib/motion";

export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { loadData().then(setData).catch((e) => setErr(String(e))); }, []);
  useEffect(() => {
    if (!data) return;
    const stop = startSmoothScroll();
    requestAnimationFrame(() => ScrollTrigger.refresh());
    return stop;
  }, [data]);

  if (err) return <main className="wrap" style={{ padding: "120px 0" }}>Could not load data.json: {err}</main>;
  if (!data) return <main aria-busy="true" style={{ minHeight: "100vh" }} />;
  return (
    <>
      <Hero data={data} />
      <main>
        <CallScene data={data} />
        <Finding data={data} />
        <Fix data={data} />
        <Curves data={data} />
        <section className="wrap" style={{ padding: "160px var(--gutter)", color: "var(--ink-3)" }}>
          <p className="mono">Sections 6–8 come next: who uses it, how it works, close.</p>
        </section>
      </main>
    </>
  );
}
