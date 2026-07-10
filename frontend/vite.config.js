import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The workspace consumes the Phase 9 REST platform. In development, requests
// to `/api` are proxied to the FastAPI backend so the browser never crosses
// origins (no CORS surprises) and the frontend stays deployment-agnostic.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Route-split pages already lazy-load; keep the vendor chunk explicit so
    // ECharts (the largest dependency) is cached independently of app code.
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ["echarts"],
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
