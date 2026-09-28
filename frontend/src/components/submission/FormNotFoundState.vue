<script setup lang="ts">
/**
 * Shown when the route in the address bar matches no form.
 *
 * A mistyped or deleted link used to sit on the loading spinner forever,
 * because the page treated "not loaded yet" and "could not be loaded" as the
 * same state. Saying so plainly is better than an indefinite wait.
 */
</script>

<template>
    <div class="flex flex-col items-center justify-center gap-2 text-center text-ink-gray-8">
        <lucide-file-question class="w-10 h-10 text-ink-gray-5" aria-hidden="true" />
        <h1 class="text-2xl font-bold">Form not found</h1>
        <p class="max-w-md text-base text-ink-gray-6">
            This link does not match any form. It may have been removed, or the address
            may be mistyped — check the link and try again.
        </p>
    </div>
</template>
