<script setup lang="ts">
import { Button } from "frappe-ui";

/**
 * Page controls for a bounded submission list.
 *
 * The range and total describe the filtered set, so "1-20 of 340" stays true
 * while a filter is on rather than quoting the form's lifetime count.
 */
defineProps<{
    rangeFrom: number;
    rangeTo: number;
    total: number;
    page: number;
    pageCount: number;
    pageLength: number;
    pageLengths: number[];
    hasMore: boolean;
    loading?: boolean;
}>();

const emit = defineEmits<{
    (e: "previous"): void;
    (e: "next"): void;
    (e: "update:pageLength", value: number): void;
}>();
</script>

<template>
    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-outline-gray-1 px-1 py-3">
        <div class="flex items-center gap-2 text-xs text-ink-gray-6">
            <span v-if="total">Showing {{ rangeFrom }}–{{ rangeTo }} of {{ total }}</span>
            <span v-else>No submissions</span>
            <span class="text-ink-gray-4">·</span>
            <label class="flex items-center gap-1.5">
                <span>Per page</span>
                <select
                    class="h-7 rounded border border-outline-gray-2 bg-surface-base px-1.5 text-xs text-ink-gray-8"
                    :value="pageLength"
                    @change="emit('update:pageLength', Number(($event.target as HTMLSelectElement).value))"
                >
                    <option v-for="size in pageLengths" :key="size" :value="size">{{ size }}</option>
                </select>
            </label>
        </div>

        <div class="flex items-center gap-2">
            <Button
                size="sm"
                variant="outline"
                icon-left="chevron-left"
                :disabled="page <= 1 || loading"
                @click="emit('previous')"
            >
                Previous
            </Button>
            <span class="text-xs text-ink-gray-6">Page {{ page }} of {{ pageCount }}</span>
            <Button
                size="sm"
                variant="outline"
                icon-right="chevron-right"
                :disabled="!hasMore || loading"
                @click="emit('next')"
            >
                Next
            </Button>
        </div>
    </div>
</template>
