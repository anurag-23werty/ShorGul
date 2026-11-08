import { lazy, Suspense, useEffect, useState } from "react";
import { Hero } from "./components/Hero";
import type { Data } from "./lib/data";
import { loadData } from "./lib/data";

const restChunk = typeof window === "undefined" ? new Promise<never>(() => {}) : import("./Rest");   // start fetching now, in parallel with data.json; render it after the hero
const Rest = lazy(() => restChunk);

export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { loadData().then(setData).catch((e) => setErr(String(e))); }, []);

  return (
    <>
      <Hero data={data} />
      {err && <main className="wrap" style={{ padding: "120px 0" }}>Could not load data.json: {err}</main>}
      {data && (
        <Suspense fallback={<div style={{ minHeight: "100vh" }} aria-busy="true" />}>
          <Rest data={data} />
        </Suspense>
      )}
      {!data && !err && <div style={{ minHeight: "100vh" }} aria-busy="true" />}
    </>
  );
}
