<script setup lang="ts">
import { Button, FormControl, Badge } from "frappe-ui";
import { computed, ref } from "vue";
import {
    VALUELESS_OPERATORS,
    LIST_OPERATORS,
    type FilterFieldOption,
    type SubmissionFilter,
} from "@/composables/useSubmissionQuery";

/**
 * Frappe-style filtering for submissions: pick a field, an operator and a value.
 *
 * Both the record's own columns and the form's own questions are offered, so
 * "everyone who answered Zurich" is as reachable as "everything that failed".
 */
const props = defineProps<{
    filters: SubmissionFilter[];
    columnFields: FilterFieldOption[];
    answerFields: FilterFieldOption[];
    operators: string[];
    search: string;
    activeFilterCount: number;
    loading?: boolean;
}>();

const emit = defineEmits<{
    (e: "update:search", value: string): void;
    (e: "add", source: "column" | "answer"): void;
    (e: "remove", index: number): void;
    (e: "apply"): void;
    (e: "clear"): void;
}>();

const open = ref(false);

const fieldsFor = (entry: SubmissionFilter) =>
    entry.source === "answer" ? props.answerFields : props.columnFields;

const operatorList = computed(() =>
    props.operators.length ? props.operators : ["=", "!=", "like", "in", "is set", "is not set"]
);

function needsValue(entry: SubmissionFilter) {
    return !VALUELESS_OPERATORS.includes(entry.operator);
}

/** `in`, `not in` and `between` read as comma-separated text but travel as a list. */
function isList(entry: SubmissionFilter) {
    return LIST_OPERATORS.includes(entry.operator);
}

function listText(entry: SubmissionFilter) {
    return Array.isArray(entry.value) ? entry.value.join(", ") : String(entry.value ?? "");
}

function setListValue(entry: SubmissionFilter, text: string) {
    entry.value = text.split(",").map((part) => part.trim()).filter(Boolean);
}

function onOperatorChange(entry: SubmissionFilter) {
    if (!needsValue(entry)) entry.value = null;
    else if (isList(entry) && !Array.isArray(entry.value)) entry.value = [];
    else if (!isList(entry) && Array.isArray(entry.value)) entry.value = "";
    emit("apply");
}
</script>

<template>
    <div class="flex flex-col gap-3">
        <div class="flex flex-wrap items-center gap-2">
            <FormControl
                type="search"
                size="sm"
                variant="outline"
                class="w-56"
                placeholder="Search submissions…"
                :modelValue="search"
                @update:modelValue="(value: string) => emit('update:search', value)"
                @keyup.enter="emit('apply')"
            />
            <Button size="sm" variant="outline" :loading="loading" @click="emit('apply')">Search</Button>

            <Button size="sm" variant="subtle" icon-left="filter" @click="open = !open">
                Filter
                <Badge v-if="activeFilterCount" class="ml-1.5" variant="solid" theme="blue" size="sm">
                    {{ activeFilterCount }}
                </Badge>
            </Button>

            <Button
                v-if="activeFilterCount || search"
                size="sm"
                variant="ghost"
                icon-left="x"
                @click="emit('clear')"
            >
                Clear
            </Button>
        </div>

        <div
            v-if="open"
            class="flex flex-col gap-2 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3"
        >
            <p v-if="!filters.length" class="text-xs text-ink-gray-5">
                No filters yet. Filter on a submission field, or on an answer the visitor gave.
            </p>

            <div v-for="(entry, index) in filters" :key="index" class="flex flex-wrap items-center gap-2">
                <Badge size="sm" :theme="entry.source === 'answer' ? 'green' : 'gray'" variant="subtle">
                    {{ entry.source === "answer" ? "Answer" : "Field" }}
                </Badge>

                <select
                    v-model="entry.field"
                    class="h-7 min-w-40 rounded border border-outline-gray-2 bg-surface-base px-2 text-xs text-ink-gray-8"
                    @change="emit('apply')"
                >
                    <option v-for="option in fieldsFor(entry)" :key="option.field" :value="option.field">
                        {{ option.label }}
                    </option>
                </select>

                <select
                    v-model="entry.operator"
                    class="h-7 w-28 rounded border border-outline-gray-2 bg-surface-base px-2 text-xs text-ink-gray-8"
                    @change="onOperatorChange(entry)"
                >
                    <option v-for="operator in operatorList" :key="operator" :value="operator">
                        {{ operator }}
                    </option>
                </select>

                <input
                    v-if="needsValue(entry) && isList(entry)"
                    :value="listText(entry)"
                    class="h-7 w-52 rounded border border-outline-gray-2 bg-surface-base px-2 text-xs text-ink-gray-8"
                    placeholder="Comma separated"
                    @input="setListValue(entry, ($event.target as HTMLInputElement).value)"
                    @keyup.enter="emit('apply')"
                />
                <input
                    v-else-if="needsValue(entry)"
                    v-model="entry.value"
                    class="h-7 w-52 rounded border border-outline-gray-2 bg-surface-base px-2 text-xs text-ink-gray-8"
                    placeholder="Value"
                    @keyup.enter="emit('apply')"
                />

                <Button size="sm" variant="ghost" icon="x" @click="emit('remove', index)" />
            </div>

            <div class="flex flex-wrap items-center gap-2 pt-1">
                <Button size="sm" variant="outline" icon-left="plus" @click="emit('add', 'column')">
                    Submission field
                </Button>
                <Button
                    v-if="answerFields.length"
                    size="sm"
                    variant="outline"
                    icon-left="plus"
                    @click="emit('add', 'answer')"
                >
                    Form answer
                </Button>
                <Button size="sm" variant="solid" :loading="loading" @click="emit('apply')">Apply</Button>
            </div>
        </div>
    </div>
</template>
