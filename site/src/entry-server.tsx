import { StrictMode } from "react";
import { renderToString } from "react-dom/server";
import App from "./App";

/** Build-time prerender of the first paint (hero only; data-driven sections mount on the client). */
export function render() {
  return renderToString(<StrictMode><App /></StrictMode>);
}
