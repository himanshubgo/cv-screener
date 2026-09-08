import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend (api.py) runs separately via `uvicorn api:app --port 8000`;
// proxy /api so the frontend can call same-origin paths in dev.
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
});
