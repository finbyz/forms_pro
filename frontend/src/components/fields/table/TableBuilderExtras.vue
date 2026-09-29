<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { FormControl, Button, createResource } from "frappe-ui";
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

// A Table field points either at a child DocType this form created, or at one
// that arrived with the target DocType -- "Allowed To Transact With" comes with
// Supplier, and its columns are shared by every supplier on the site. Only the
// first kind is ours to edit; the server decides and says so here. There is no
// way to attach some other table by hand: a form gets the tables its DocType
// already has, or one it builds itself, and nothing in between.
const editable = ref(false);

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
            <Button
                variant="solid"
                size="sm"
                :loading="busy"
                label="Create table"
                @click="createTable"
            />
        </div>

        <template v-else>
            <span class="text-xs text-ink-gray-5 truncate" :title="childDoctype">
                Table:
                <span class="font-medium text-ink-gray-7">{{ childDoctype }}</span>
            </span>

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
                    This table came with {{ childDoctype }} and is shared across the site, so
                    its columns are fixed here. Change them in ERPNext if they need to differ.
                </p>
            </template>
        </template>
    </div>
</template>
