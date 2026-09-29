<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { FormControl, Button, Dialog, createResource } from "frappe-ui";
import { Trash2 } from "@lucide/vue";
import { toast } from "vue-sonner";
import { useEditForm } from "@/stores/editForm";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const props = defineProps<{ field: Record<string, any> }>();
const emit = defineEmits<{ (e: "update:field", value: typeof props.field): void }>();

const editFormStore = useEditForm();

type Column = { label: string; fieldtype: string; fieldname?: string; reqd?: number };

const COLUMN_TYPES = [
    "Data",
    "Number",
    "Email",
    "Phone",
    "Date",
    "Date Time",
    "Time Picker",
    "Select",
    "Checkbox",
    "Textarea",
    "Link",
    // Lets a table hold one file per row, which is how a form offers multiple
    // file uploads -- there is no multi-file field type.
    "Attach",
    "Currency",
    "URL",
];

const columns = ref<Column[]>([]);
const busy = ref(false);

// A Table field can point at a child DocType the form created, or at one that
// belongs to an app -- "Allowed To Transact With" on Supplier is ERPNext's, and
// its columns are shared by every supplier on the site. Only the first kind is
// ours to edit; the server decides and says so here.
const editable = ref(false);

// Picking an existing table instead of building one: the site already has the
// tables ERPNext ships and every table a previous form generated, and reusing
// one keeps the answers where the rest of the system already reads them.
const picking = ref(false);
const search = ref("");
const matches = ref<{ name: string; module: string; editable: boolean; column_count: number }[]>([]);
const searching = ref(false);

async function findTables() {
    const formId = editFormStore.currentFormId;
    if (!formId) return;
    searching.value = true;
    try {
        const res = createResource({
            url: "forms_pro.api.v1.builder.child_tables.search_child_tables",
            params: { form_id: formId, search: search.value },
        });
        await res.fetch();
        matches.value = res.data?.tables ?? [];
    } catch (e: any) {
        toast.error("Could not load tables", { description: e?.message });
    } finally {
        searching.value = false;
    }
}

function openPicker() {
    picking.value = true;
    search.value = "";
    findTables();
}

async function linkTable(name: string) {
    // Same reason as createTable: assign onto the live field, do not replace it.
    props.field.options = name;
    emit("update:field", props.field);
    picking.value = false;
    await loadColumns();
    await editFormStore.refreshPublishState();
    toast.success(`Linked "${name}"`);
}

function unlinkTable() {
    props.field.options = "";
    emit("update:field", props.field);
    columns.value = [];
    editable.value = false;
}

// A Table field stores its backing child DocType in `options`.
const childDoctype = computed(() => props.field.options || "");

async function loadColumns() {
    if (!childDoctype.value) {
        columns.value = [];
        editable.value = false;
        return;
    }
    const res = createResource({
        url: "forms_pro.api.v1.builder.child_tables.get_child_table_columns",
        params: { doctype: childDoctype.value },
    });
    await res.fetch();
    editable.value = Boolean(res.data?.editable);
    columns.value = (res.data?.columns ?? []).map((c: Column) => ({
        label: c.label,
        fieldtype: c.fieldtype,
        fieldname: c.fieldname,
        reqd: c.reqd,
    }));
}

watch(childDoctype, loadColumns, { immediate: true });

async function createTable() {
    const formId = editFormStore.currentFormId;
    if (!formId) return;
    busy.value = true;
    try {
        const res = createResource({
            url: "forms_pro.api.v1.builder.child_tables.create_child_table",
            method: "POST",
            makeParams: () => ({
                form_id: formId,
                field_label: props.field.label || "Table",
            }),
        });
        await res.fetch();

        // Assign onto the field the store already holds, rather than emitting a
        // replacement object: the parent binds the live field, so a new object
        // was dropped and `options` stayed empty -- the table was created on the
        // server while the builder still offered "Create table" and showed no
        // columns until the panel was reopened.
        props.field.options = res.data.doctype;
        emit("update:field", props.field);

        await loadColumns();
        toast.success(`Created table "${res.data.doctype}"`);
    } catch (e: any) {
        toast.error("Could not create the table", { description: e?.message });
    } finally {
        busy.value = false;
    }
}

function addColumn() {
    columns.value.push({ label: "", fieldtype: "Data" });
}

function removeColumn(index: number) {
    columns.value.splice(index, 1);
}

async function saveColumns() {
    const cleaned = columns.value.filter((c) => c.label.trim());
    if (!cleaned.length) {
        toast.error("A table needs at least one column.");
        return;
    }
    busy.value = true;
    try {
        const res = createResource({
            url: "forms_pro.api.v1.builder.child_tables.set_child_table_columns",
            method: "POST",
            makeParams: () => ({ doctype: childDoctype.value, columns: cleaned }),
        });
        await res.fetch();
        columns.value = res.data?.columns ?? cleaned;
        // Columns are stored on the child DocType, not on the form, so nothing
        // the form watches changed. Without this the author saw no "Saving..."
        // and no "Publish changes" until they edited something unrelated.
        await editFormStore.refreshPublishState();
        toast.success("Columns saved");
    } catch (e: any) {
        toast.error("Could not save columns", { description: e?.message });
    } finally {
        busy.value = false;
    }
}
</script>

<template>
    <div class="flex flex-col gap-2 w-full">
        <!-- No backing child table yet -->
        <div
            v-if="!childDoctype"
            class="rounded-md border border-dashed border-outline-gray-2 bg-surface-gray-1 p-3 text-center"
        >
            <p class="text-xs text-ink-gray-6">This table has no columns yet.</p>
            <p class="mt-1 mb-2 text-xs text-ink-gray-5">
                A table is stored as its own child DocType, named after this form and field.
            </p>
            <div class="flex items-center justify-center gap-2">
                <Button
                    variant="solid"
                    size="sm"
                    :loading="busy"
                    label="Create table"
                    @click="createTable"
                />
                <Button
                    variant="subtle"
                    size="sm"
                    label="Link existing table"
                    @click="openPicker"
                />
            </div>
        </div>

        <template v-else>
            <div class="flex items-center justify-between gap-2">
                <span class="text-xs text-ink-gray-5 truncate" :title="childDoctype">
                    Table:
                    <span class="font-medium text-ink-gray-7">{{ childDoctype }}</span>
                </span>
                <Button variant="ghost" size="sm" label="Change" @click="openPicker" />
            </div>

            <template v-if="editable">
                <div v-for="(col, i) in columns" :key="i" class="flex items-end gap-1.5">
                    <FormControl
                        v-model="col.label"
                        type="text"
                        size="sm"
                        variant="outline"
                        placeholder="Column name"
                        class="flex-1 min-w-0"
                    />
                    <FormControl
                        v-model="col.fieldtype"
                        type="select"
                        size="sm"
                        variant="outline"
                        :options="COLUMN_TYPES"
                        class="w-28 shrink-0"
                    />
                    <Button
                        variant="ghost"
                        size="sm"
                        theme="red"
                        aria-label="Remove column"
                        @click="removeColumn(i)"
                    >
                        <Trash2 class="w-4 h-4" aria-hidden="true" />
                    </Button>
                </div>

                <div class="flex gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        icon-left="plus"
                        label="Add column"
                        @click="addColumn"
                    />
                    <Button
                        variant="subtle"
                        size="sm"
                        :loading="busy"
                        label="Save columns"
                        @click="saveColumns"
                    />
                </div>
            </template>

            <template v-else>
                <ul class="flex flex-col gap-1">
                    <li
                        v-for="col in columns"
                        :key="col.fieldname"
                        class="flex items-center justify-between gap-2 rounded border border-outline-gray-1 bg-surface-gray-1 px-2 py-1.5"
                    >
                        <span class="text-xs text-ink-gray-7 truncate">{{ col.label }}</span>
                        <span class="text-xs text-ink-gray-5 shrink-0">{{ col.fieldtype }}</span>
                    </li>
                </ul>
                <p class="text-xs text-ink-gray-5">
                    This table belongs to another app and is shared across the site, so its
                    columns are fixed here. Change them in ERPNext if they need to differ.
                </p>
            </template>
        </template>

        <Dialog
            v-model="picking"
            :options="{ title: 'Link an existing table', size: 'lg' }"
        >
            <template #body-content>
                <div class="flex flex-col gap-3">
                    <FormControl
                        v-model="search"
                        type="text"
                        size="sm"
                        variant="outline"
                        placeholder="Search tables by name"
                        @input="findTables"
                    />
                    <p v-if="searching" class="text-xs text-ink-gray-5">Searching...</p>
                    <p v-else-if="!matches.length" class="text-xs text-ink-gray-5">
                        No table matches that name.
                    </p>
                    <ul v-else class="flex flex-col gap-1 max-h-80 overflow-y-auto">
                        <li v-for="table in matches" :key="table.name">
                            <button
                                type="button"
                                class="w-full flex items-center justify-between gap-3 rounded border border-outline-gray-1 px-3 py-2 text-left hover:bg-surface-gray-2"
                                @click="linkTable(table.name)"
                            >
                                <span class="min-w-0">
                                    <span class="block text-sm text-ink-gray-8 truncate">{{ table.name }}</span>
                                    <span class="block text-xs text-ink-gray-5">{{ table.module }}</span>
                                </span>
                                <span class="shrink-0 text-xs text-ink-gray-5">
                                    {{ table.column_count }} columns
                                    <template v-if="!table.editable"> · read-only</template>
                                </span>
                            </button>
                        </li>
                    </ul>
                    <Button
                        v-if="childDoctype"
                        variant="ghost"
                        theme="red"
                        size="sm"
                        class="self-start"
                        label="Unlink this table"
                        @click="unlinkTable(); picking = false"
                    />
                </div>
            </template>
        </Dialog>
    </div>
</template>
