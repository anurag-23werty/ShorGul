import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import App from "./App";
import "@fontsource-variable/geist/wght.css";
import "@fontsource-variable/geist-mono/wght.css";
import "@fontsource/noto-sans-devanagari/400.css";
import "@fontsource/noto-sans-devanagari/500.css";
import "./styles/global.css";

const root = document.getElementById("root")!;
const app = <StrictMode><App /></StrictMode>;
if (root.firstElementChild) hydrateRoot(root, app);   // prerendered hero (production build)
else createRoot(root).render(app);                    // dev server
