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
 * Frappe-style filtering for submissions:
 * Unified field selector (Form Questions & Submission Details),
 * Frappe-standard operators, dropdown options for select fields,
 * and seamless comma-separated value input for list operators.
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
    (e: "add", arg?: any): void;
    (e: "remove", index: number): void;
    (e: "apply"): void;
    (e: "clear"): void;
}>();

const open = ref(false);

const OPERATOR_LABELS: Record<string, string> = {
    "=": "Equals (=)",
    "!=": "Not Equals (!=)",
    "like": "Like",
    "not like": "Not Like",
    "in": "In",
    "not in": "Not In",
    ">": "Greater Than (>)",
    "<": "Less Than (<)",
    ">=": "Greater Than Or Equal To (>=)",
    "<=": "Less Than Or Equal To (<=)",
    "between": "Between",
    "is set": "Is Set",
    "is not set": "Is Not Set",
};

const DEFAULT_OPERATORS = [
    "=",
    "!=",
    "like",
    "not like",
    "in",
    "not in",
    ">",
    "<",
    ">=",
    "<=",
    "between",
    "is set",
    "is not set",
];

const operatorList = computed(() => {
    const list = props.operators.length ? props.operators : DEFAULT_OPERATORS;
    return list.map((op) => ({
        value: op,
        label: OPERATOR_LABELS[op] || op,
    }));
});

function getFieldKey(entry: SubmissionFilter): string {
    return `${entry.source || "column"}:${entry.field}`;
}

function setFieldKey(entry: SubmissionFilter, key: string) {
    const colonIdx = key.indexOf(":");
    if (colonIdx !== -1) {
        entry.source = key.slice(0, colonIdx) as "column" | "answer";
        entry.field = key.slice(colonIdx + 1);
    } else {
        entry.field = key;
    }
    entry.value = "";
}

function getFieldDef(entry: SubmissionFilter): FilterFieldOption | undefined {
    const pool = entry.source === "answer" ? props.answerFields : props.columnFields;
    return pool.find((f) => f.field === entry.field);
}

function getFieldOptions(entry: SubmissionFilter): string[] {
    const def = getFieldDef(entry);
    if (!def?.options) return [];
    if (typeof def.options === "string") {
        return def.options.split("\n").map((o) => o.trim()).filter(Boolean);
    }
    return [];
}

function needsValue(entry: SubmissionFilter): boolean {
    return !VALUELESS_OPERATORS.includes(entry.operator);
}

function isList(entry: SubmissionFilter): boolean {
    return LIST_OPERATORS.includes(entry.operator);
}

function onOperatorChange(entry: SubmissionFilter) {
    if (!needsValue(entry)) {
        entry.value = null;
    } else if (entry.value === null || entry.value === undefined) {
        entry.value = "";
    } else if (Array.isArray(entry.value)) {
        entry.value = entry.value.join(", ");
    }
}

function onAddFilter() {
    let source: "column" | "answer" = "column";
    let field = "";

    if (props.answerFields.length) {
        source = "answer";
        field = props.answerFields[0].field;
    } else if (props.columnFields.length) {
        source = "column";
        field = props.columnFields[0].field;
    }
    emit("add", { source, field });
}
</script>

<template>
    <div class="flex flex-col gap-3">
        <!-- Top Toolbar -->
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

            <Button
                size="sm"
                :variant="open || activeFilterCount ? 'solid' : 'subtle'"
                :theme="activeFilterCount ? 'blue' : 'gray'"
                icon-left="filter"
                @click="open = !open"
            >
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

        <!-- Filter Panel -->
        <div
            v-if="open"
            class="flex flex-col gap-2.5 rounded-xl border border-outline-gray-2 bg-surface-gray-1 p-3.5 shadow-xs"
        >
            <div v-if="!filters.length" class="py-2 text-center text-xs text-ink-gray-5">
                No filters applied. Click <strong>Add Filter</strong> to filter submissions.
            </div>

            <!-- Filter Rows -->
            <div
                v-for="(entry, index) in filters"
                :key="index"
                class="flex flex-wrap items-center gap-2 bg-surface-base p-2 rounded-lg border border-outline-gray-2/70 shadow-2xs"
            >
                <!-- Field selector -->
                <select
                    :value="getFieldKey(entry)"
                    class="h-8 min-w-44 max-w-60 rounded-md border border-outline-gray-2 bg-surface-base px-2.5 text-xs text-ink-gray-9 shadow-2xs focus:border-outline-gray-3 focus:outline-none"
                    @change="setFieldKey(entry, ($event.target as HTMLSelectElement).value)"
                >
                    <optgroup v-if="answerFields.length" label="Form Questions">
                        <option
                            v-for="opt in answerFields"
                            :key="'answer:' + opt.field"
                            :value="'answer:' + opt.field"
                        >
                            {{ opt.label }}
                        </option>
                    </optgroup>
                    <optgroup label="Submission Details">
                        <option
                            v-for="opt in columnFields"
                            :key="'column:' + opt.field"
                            :value="'column:' + opt.field"
                        >
                            {{ opt.label }}
                        </option>
                    </optgroup>
                </select>

                <!-- Operator selector -->
                <select
                    v-model="entry.operator"
                    class="h-8 min-w-36 rounded-md border border-outline-gray-2 bg-surface-base px-2.5 text-xs text-ink-gray-9 shadow-2xs focus:border-outline-gray-3 focus:outline-none"
                    @change="onOperatorChange(entry)"
                >
                    <option v-for="op in operatorList" :key="op.value" :value="op.value">
                        {{ op.label }}
                    </option>
                </select>

                <!-- Value: Select with predefined options (when available and operator is = or !=) -->
                <select
                    v-if="needsValue(entry) && getFieldOptions(entry).length > 0 && (entry.operator === '=' || entry.operator === '!=')"
                    v-model="entry.value"
                    class="h-8 min-w-48 flex-1 rounded-md border border-outline-gray-2 bg-surface-base px-2.5 text-xs text-ink-gray-9 shadow-2xs focus:border-outline-gray-3 focus:outline-none"
                    @keyup.enter="emit('apply')"
                >
                    <option value="">Select option...</option>
                    <option v-for="opt in getFieldOptions(entry)" :key="opt" :value="opt">
                        {{ opt }}
                    </option>
                </select>

                <!-- Value: List input for 'in' / 'not in' (plain input allowing commas) -->
                <input
                    v-else-if="needsValue(entry) && isList(entry)"
                    v-model="entry.value"
                    type="text"
                    class="h-8 min-w-48 flex-1 rounded-md border border-outline-gray-2 bg-surface-base px-2.5 text-xs text-ink-gray-9 shadow-2xs focus:border-outline-gray-3 focus:outline-none placeholder:text-ink-gray-4"
                    placeholder="Comma-separated values (e.g. A, B)"
                    @keyup.enter="emit('apply')"
                />

                <!-- Value: Between input -->
                <input
                    v-else-if="needsValue(entry) && entry.operator === 'between'"
                    v-model="entry.value"
                    type="text"
                    class="h-8 min-w-48 flex-1 rounded-md border border-outline-gray-2 bg-surface-base px-2.5 text-xs text-ink-gray-9 shadow-2xs focus:border-outline-gray-3 focus:outline-none placeholder:text-ink-gray-4"
                    placeholder="Value 1, Value 2"
                    @keyup.enter="emit('apply')"
                />

                <!-- Value: Standard text input -->
                <input
                    v-else-if="needsValue(entry)"
                    v-model="entry.value"
                    type="text"
                    class="h-8 min-w-48 flex-1 rounded-md border border-outline-gray-2 bg-surface-base px-2.5 text-xs text-ink-gray-9 shadow-2xs focus:border-outline-gray-3 focus:outline-none placeholder:text-ink-gray-4"
                    placeholder="Value"
                    @keyup.enter="emit('apply')"
                />

                <!-- Remove row -->
                <Button
                    size="sm"
                    variant="ghost"
                    icon="x"
                    class="text-ink-gray-5 hover:text-ink-gray-9"
                    @click="emit('remove', index)"
                />
            </div>

            <!-- Action footer -->
            <div class="flex items-center justify-between pt-2 border-t border-outline-gray-2/60 mt-1">
                <Button
                    size="sm"
                    variant="outline"
                    icon-left="plus"
                    @click="onAddFilter"
                >
                    Add Filter
                </Button>

                <div class="flex items-center gap-2">
                    <Button
                        v-if="filters.length"
                        size="sm"
                        variant="ghost"
                        @click="emit('clear')"
                    >
                        Clear All
                    </Button>
                    <Button
                        size="sm"
                        variant="solid"
                        :loading="loading"
                        @click="emit('apply')"
                    >
                        Apply Filters
                    </Button>
                </div>
            </div>
        </div>
    </div>
</template>
