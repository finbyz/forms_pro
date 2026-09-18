import { defineStore } from "pinia";
import { ref, watch } from "vue";

export const useThemeStore = defineStore("theme", () => {
    const tokens = ref({
        font_family: "Inter",
        primary_color: "#1D4ED8",
        background_color: "#FFFFFF",
        input_radius: "8px",
        card_radius: "12px",
    });

    const applyTokens = () => {
        const root = document.documentElement;
        root.style.setProperty("--fp-font-family", tokens.value.font_family);
        root.style.setProperty("--fp-primary-color", tokens.value.primary_color);
        root.style.setProperty("--fp-background-color", tokens.value.background_color);
        root.style.setProperty("--fp-input-radius", tokens.value.input_radius);
        root.style.setProperty("--fp-card-radius", tokens.value.card_radius);
    };

    watch(tokens, () => applyTokens(), { deep: true });

    return { tokens, applyTokens };
});
