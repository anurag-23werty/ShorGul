import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" so the build works on GitHub Pages sub-paths and Vercel alike
export default defineConfig({ base: "./", plugins: [react()] });
