import path from "node:path";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        frappeui({
            frappeProxy: true,
            jinjaBootData: true,
            lucideIcons: true,
            buildConfig: {
                // The /forms route serves www/forms.py + forms.html (see
                // hooks.py website_route_rules). Write the entry there directly so a
                // plain `vite build` is complete — frontend.html has no .py beside it
                // and was never served.
                indexHtmlPath: "../forms_pro/www/forms.html",
                emptyOutDir: true,
                sourcemap: false,
            },
        }),
        vue(),
    ],
    build: {
        chunkSizeWarningLimit: 1500,
        outDir: "../forms_pro/public/frontend",
        emptyOutDir: true,
        target: "es2015",
        sourcemap: false,
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "src"),
            // Deep alias so the rich-text editor can be code-split on its own.
            // The package's exports map has no subpath for it, and going through
            // the barrel would pull ProseMirror into the eager graph.
            "frappe-ui-text-editor": path.resolve(
                __dirname,
                "node_modules/frappe-ui/src/components/TextEditor/TextEditor.vue"
            ),
            "tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
        },
    },
    optimizeDeps: {
        include: ["feather-icons", "showdown", "highlight.js/lib/core", "interactjs"],
        exclude: ["frappe-ui"],
    },
    server: {
        allowedHosts: true,
    },
});
