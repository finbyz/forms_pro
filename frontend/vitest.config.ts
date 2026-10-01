import { fileURLToPath } from "node:url";
import path from "node:path";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vitest/config";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  // Lets a test import a store that reaches .vue components and frappe-ui's
  // icons; a test that needs a DOM opts in with `@vitest-environment jsdom`.
  plugins: [
    frappeui({ lucideIcons: true, frappeProxy: false, jinjaBootData: false, buildConfig: false }),
    vue(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
    server: { deps: { inline: ["frappe-ui"] } },
  },
});
