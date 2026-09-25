<script setup lang="ts">
/**
 * Attribution badge on the public form.
 *
 * Sits bottom-left because Google's invisible reCAPTCHA badge occupies the
 * bottom-right of the same viewport.
 */
import { ArrowUpRight } from "@lucide/vue";

withDefaults(
    defineProps<{
        label?: string;
        company?: string;
        href?: string;
    }>(),
    {
        label: "Built by",
        company: "FinByz Tech",
        href: "https://finbyz.tech",
    }
);
</script>

<template>
    <a
        :href="href"
        target="_blank"
        rel="noopener noreferrer"
        :aria-label="`${label} ${company} — opens finbyz.tech in a new tab`"
        class="group fixed bottom-4 left-4 z-40 inline-flex items-center gap-1.5 rounded border border-outline-gray-2 bg-surface-white/90 px-2.5 py-1.5 shadow-sm backdrop-blur-sm transition-all duration-200 ease-out hover:border-outline-gray-3 hover:bg-surface-white hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 motion-reduce:transition-none"
    >
        <span class="text-xs text-ink-gray-5">{{ label }}</span>
        <span class="text-xs font-medium text-ink-gray-8">{{ company }}</span>
        <ArrowUpRight
            class="size-3 text-ink-gray-4 transition-transform duration-200 group-hover:-translate-y-px group-hover:translate-x-px group-hover:text-ink-gray-6 motion-reduce:transition-none"
            aria-hidden="true"
        />
    </a>
</template>
