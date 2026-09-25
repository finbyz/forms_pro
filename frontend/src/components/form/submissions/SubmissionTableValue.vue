<script setup lang="ts">
import { Badge, createResource } from "frappe-ui";
import { computed, watch } from "vue";

const props = defineProps<{
    label: string;
    description?: string;
    options?: string;
    value: any;
}>();

const IGNORED_FIELDS = new Set([
    "name",
    "owner",
    "creation",
    "modified",
    "modified_by",
    "docstatus",
    "idx",
    "parent",
    "parentfield",
    "parenttype",
    "doctype",
]);

interface ColumnDef {
    key: string;
    label: string;
    fieldtype?: string;
}

const rows = computed<Record<string, any>[]>(() => {
    if (!props.value) return [];
    if (Array.isArray(props.value)) return props.value;
    if (typeof props.value === "string") {
        try {
            const parsed = JSON.parse(props.value);
            if (Array.isArray(parsed)) return parsed;
        } catch {
            return [];
        }
    }
    return [];
});

const columnResource = createResource({
    url: "forms_pro.api.form.get_doctype_fields",
    makeParams() {
        return {
            doctype: props.options || "",
        };
    },
});

watch(
    () => props.options,
    (doctype) => {
        if (doctype) {
            columnResource.fetch();
        }
    },
    { immediate: true }
);

function humanize(str: string): string {
    return str
        .replace(/_/g, " ")
        .replace(/\b\w/g, (l) => l.toUpperCase());
}

const columns = computed<ColumnDef[]>(() => {
    const cols: ColumnDef[] = [];
    const seenKeys = new Set<string>();

    // 1. If child doctype fields are fetched, use them first
    const doctypeFields = Array.isArray(columnResource.data) ? columnResource.data : [];
    for (const f of doctypeFields) {
        if (f.fieldname && !IGNORED_FIELDS.has(f.fieldname) && !f.hidden) {
            cols.push({
                key: f.fieldname,
                label: f.label || humanize(f.fieldname),
                fieldtype: f.fieldtype,
            });
            seenKeys.add(f.fieldname);
        }
    }

    // 2. Also check row keys in case custom fields or extra keys exist that were not in child doctype
    for (const row of rows.value) {
        if (row && typeof row === "object") {
            for (const key of Object.keys(row)) {
                if (!IGNORED_FIELDS.has(key) && !seenKeys.has(key)) {
                    cols.push({
                        key,
                        label: humanize(key),
                    });
                    seenKeys.add(key);
                }
            }
        }
    }

    return cols;
});

function formatCellValue(val: any): string {
    if (val === null || val === undefined || val === "") return "–";
    if (typeof val === "boolean") return val ? "Yes" : "No";
    if (typeof val === "object") {
        try {
            return JSON.stringify(val);
        } catch {
            return String(val);
        }
    }
    return String(val);
}
</script>

<template>
    <div class="flex flex-col gap-2 w-full my-2">
        <!-- Table Label Header -->
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-ink-gray-8">{{ label }}</span>
                <Badge
                    v-if="rows.length"
                    variant="subtle"
                    theme="gray"
                    size="sm"
                    :label="`${rows.length} ${rows.length === 1 ? 'row' : 'rows'}`"
                />
            </div>
            <span v-if="options" class="text-xs text-ink-gray-5 font-mono">{{ options }}</span>
        </div>
        <p v-if="description" class="text-xs text-ink-gray-5">{{ description }}</p>

        <!-- Table Container -->
        <div class="border border-outline-gray-2 rounded-6 overflow-hidden bg-surface-white">
            <div class="overflow-x-auto max-w-full">
                <table v-if="rows.length && columns.length" class="w-full text-left text-sm border-collapse">
                    <thead>
                        <tr class="bg-surface-gray-2 border-b border-outline-gray-2">
                            <th class="w-10 px-3 py-2 text-center text-xs font-medium text-ink-gray-5 uppercase tracking-wider select-none">
                                #
                            </th>
                            <th
                                v-for="col in columns"
                                :key="col.key"
                                class="px-3 py-2 text-left text-xs font-semibold text-ink-gray-7 uppercase tracking-wider whitespace-nowrap"
                            >
                                {{ col.label }}
                            </th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-outline-gray-1">
                        <tr
                            v-for="(row, rIdx) in rows"
                            :key="rIdx"
                            class="hover:bg-surface-gray-1/60 transition-colors"
                        >
                            <td class="w-10 px-3 py-2.5 text-center text-xs text-ink-gray-4 font-mono select-none">
                                {{ rIdx + 1 }}
                            </td>
                            <td
                                v-for="col in columns"
                                :key="col.key"
                                class="px-3 py-2.5 text-sm text-ink-gray-8 whitespace-nowrap"
                            >
                                <Badge
                                    v-if="typeof row[col.key] === 'boolean'"
                                    variant="subtle"
                                    :theme="row[col.key] ? 'green' : 'gray'"
                                    size="sm"
                                    :label="row[col.key] ? 'Yes' : 'No'"
                                />
                                <span v-else>
                                    {{ formatCellValue(row[col.key]) }}
                                </span>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <div v-else class="py-6 px-4 flex flex-col items-center justify-center gap-1 bg-surface-gray-1/40">
                    <p class="text-sm font-medium text-ink-gray-6">No rows in this table</p>
                    <p class="text-xs text-ink-gray-4">This child table was submitted with no entries.</p>
                </div>
            </div>
        </div>
    </div>
</template>
