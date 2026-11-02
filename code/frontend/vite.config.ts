import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  server: { proxy: { "/api": { target: "http://127.0.0.1:8001", changeOrigin: false } } },
  preview: { proxy: { "/api": { target: "http://127.0.0.1:8001", changeOrigin: false } } },
  plugins: [vue()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
});

