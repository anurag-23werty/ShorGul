// Injects the server-rendered hero into dist/index.html so the headline paints before any JS runs.
import { readFileSync, rmSync, writeFileSync } from "node:fs";
const { render } = await import("./dist-ssr/entry-server.js");
const html = readFileSync("dist/index.html", "utf8");
if (!html.includes("<!--app-->")) throw new Error("dist/index.html has no <!--app--> placeholder");
writeFileSync("dist/index.html", html.replace("<!--app-->", render()));
rmSync("dist-ssr", { recursive: true, force: true });
console.log("[prerender] hero injected into dist/index.html");
