import { onMounted, onUnmounted } from "vue";
import { useEditForm } from "@/stores/editForm";

export function useKeyboardShortcuts() {
    const store = useEditForm();

    function handler(e: KeyboardEvent) {
        const isMac = navigator.platform.toUpperCase().includes("MAC");
        const mod = isMac ? e.metaKey : e.ctrlKey;

        if (mod && e.key === "z" && !e.shiftKey) {
            e.preventDefault();
            store.undo();
        } else if (mod && (e.key === "Z" || (e.key === "z" && e.shiftKey))) {
            e.preventDefault();
            store.redo();
        }
    }

    onMounted(() => window.addEventListener("keydown", handler));
    onUnmounted(() => window.removeEventListener("keydown", handler));
}