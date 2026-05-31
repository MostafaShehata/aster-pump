import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite builds the React app into the dist folder. Docker only packages dist.
export default defineConfig({
  plugins: [react()],
});
