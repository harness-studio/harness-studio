import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Dev proxy so the dashboard can call the backend without CORS in local dev.
  server: { proxy: { "/counters": "http://localhost:8000", "/events": "http://localhost:8000" } },
});
