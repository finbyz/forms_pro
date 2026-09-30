<script setup lang="ts">
import { useEditForm } from "@/stores/editForm";
import { formFields, FormFields } from "@/utils/form_fields";
import { ref, computed, watch } from "vue";
import type { Component } from "vue";
import type { FormField } from "@/types/formfield";
import { toast } from "vue-sonner";
import { Badge, createResource } from "frappe-ui";
import { writeDragPayload } from "@/utils/canvasDropTarget";

const editFormStore = useEditForm();

/** The canvas reads plain `dataTransfer`, so this list is just draggable divs. */
function onDragStart(event: DragEvent, field: any) {
    writeDragPayload(event, { source: "doctype", fieldname: field.fieldname });
    editFormStore.setDragging(true);
}

const componentMap = formFields.reduce((acc: Record<string, Component>, field: FormFields) => {
    acc[field.name] = field.component;
    return acc;
}, {});

const search = ref("");

const filteredFields = computed(() => {
    return editFormStore.doctypeFields.filter((field: FormField) => {
        return (field.label ?? "").toLowerCase().includes(search.value.toLowerCase());
    });
});

// A copy, not the computed itself: the list is read during a drag and should
// not change underneath it when the search box is typed into.
const draggableFields = ref<FormField[]>([]);
watch(filteredFields, (v) => (draggableFields.value = [...v]), { immediate: true });

const hasDoctype = computed(() => !!editFormStore.formData?.target_doctype);

/** True when this form generated its target DocType, rather than being pointed at one. */
const ownsDoctype = computed(() => Boolean(editFormStore.targetInfo?.owned));
const targetModule = computed(() => editFormStore.targetInfo?.module ?? "");

// Mandatory DocType fields the form does not map yet.
const missingRequired = computed(() => {
    const mapped = new Set(
        (editFormStore.fields ?? []).map((f: FormField) => f.target_field).filter(Boolean)
    );
    return (editFormStore.doctypeFields ?? []).filter(
        (f: any) => f.reqd && !mapped.has(f.fieldname)
    );
});

const doctypeList = createResource({
    url: "forms_pro.api.form.get_doctype_list",
    method: "GET",
    auto: true,
});

const doctypeOptions = computed(() =>
    (doctypeList.data ?? []).map((name: string) => ({ label: name, value: name }))
);

async function pickDoctype(v: { value: string } | string) {
    const doctype = typeof v === "string" ? v : v?.value;
    if (!doctype) return;
    const { changed, seeded, hadMappings } = await editFormStore.setTargetDoctype(doctype);
    if (!changed) return;
    if (hadMappings) {
        toast.warning("Target DocType changed — existing field mappings need review.");
    } else if (seeded) {
        toast.success(`Added ${seeded} required field${seeded === 1 ? "" : "s"} from ${doctype}`);
    } else {
        toast.success(`Now using ${doctype}`);
    }
}

function addAllRequired() {
    const added = editFormStore.seedMandatoryFields();
    if (added) toast.success(`Added ${added} required field${added === 1 ? "" : "s"}`);
}
</script>

<template>
    <div class="flex flex-col gap-3">
        <div class="flex flex-col gap-1">
            <h3 class="text-sm-semibold text-ink-gray-8">DocType Fields</h3>
            <p class="text-xs text-ink-gray-5">
                Drag a field onto the canvas, or click <span class="font-medium">+</span> to append it.
            </p>
        </div>

        <!-- Either no DocType, or one with nothing usable (e.g. the empty
             placeholder DocType created with a blank form). Both are dead ends
             without a way to switch, so offer the picker right here. -->
        <div
            v-if="!hasDoctype || filteredFields.length === 0 && !search"
            class="flex flex-col gap-2 rounded-md border border-dashed border-outline-gray-2 bg-surface-gray-1 p-3"
        >
            <p class="text-xs text-ink-gray-6">
                <template v-if="!hasDoctype">No target DocType set.</template>
                <template v-else>
                    <span class="font-medium">{{ editFormStore.formData?.target_doctype }}</span>
                    has no usable fields.
                </template>
            </p>
            <p class="text-xs text-ink-gray-5">Pick the DocType this form should write to:</p>
            <FormControl
                type="autocomplete"
                variant="outline"
                size="sm"
                placeholder="Search DocType…"
                :options="doctypeOptions"
                :modelValue="editFormStore.formData?.target_doctype"
                @update:modelValue="pickDoctype"
            />
        </div>

        <template v-if="hasDoctype">
            <!--
                Which DocType this form writes to, and whether it is one the
                form made or one the site already had. The distinction decides
                what is safe to change: a generated DocType belongs to this
                form alone, while Supplier or Contact is shared with everything
                else on the site.
            -->
            <div class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5">
                <p class="text-[10px] font-semibold uppercase tracking-wider text-ink-gray-5">
                    Writes to
                </p>
                <p
                    class="mt-0.5 text-sm font-medium text-ink-gray-8 truncate"
                    :title="editFormStore.formData?.target_doctype"
                >
                    {{ editFormStore.formData?.target_doctype }}
                </p>
                <div class="mt-1.5 flex items-center gap-1.5">
                    <Badge
                        :theme="ownsDoctype ? 'blue' : 'orange'"
                        variant="subtle"
                        size="sm"
                        :label="ownsDoctype ? 'Created by this form' : 'Existing DocType'"
                    />
                    <span v-if="targetModule" class="text-xs text-ink-gray-5 truncate">
                        {{ targetModule }}
                    </span>
                </div>
                <p class="mt-1.5 text-xs text-ink-gray-5">
                    <template v-if="ownsDoctype">
                        Fields you add here become columns on it.
                    </template>
                    <template v-else>
                        Shared with the rest of the site, so the form never changes its
                        fields.
                    </template>
                </p>
            </div>

            <FormControl
                v-model="search"
                type="search"
                variant="outline"
                placeholder="Search Fields"
                size="sm"
            />

            <Button
                v-if="missingRequired.length"
                variant="subtle"
                size="sm"
                icon-left="alert-circle"
                :label="`Add ${missingRequired.length} required field${missingRequired.length === 1 ? '' : 's'}`"
                @click="addAllRequired"
            />

            <div class="flex flex-col gap-2">
                <div
                    v-for="field in draggableFields"
                    :key="field.fieldname"
                    draggable="true"
                    class="p-2 bg-surface-gray-1 rounded-md flex flex-col gap-2 border border-outline-gray-2 hover:border-outline-gray-3 hover:bg-surface-gray-2 cursor-grab active:cursor-grabbing transition-all relative group"
                    @dragstart="onDragStart($event, field)"
                    @dragend="editFormStore.setDragging(false)"
                >
                    <div class="flex items-center gap-1.5">
                        <span class="text-xs font-medium text-ink-gray-7 truncate">{{ field.label }}</span>
                        <span v-if="field.reqd" class="text-red-500 text-xs leading-none" title="Mandatory">*</span>
                    </div>
                    <component
                        class="pointer-events-none"
                        variant="outline"
                        size="sm"
                        :is="componentMap[field.fieldtype]"
                    />
                    <Button
                        class="absolute top-3 -right-2.5 opacity-0 group-hover:opacity-100 transition-opacity z-10 shadow-sm"
                        variant="outline"
                        size="sm"
                        icon="plus"
                        @click="editFormStore.addFieldFromDoctype(field)"
                    />
                </div>
            </div>

            <p
                v-if="filteredFields.length === 0 && search"
                class="text-xs text-ink-gray-5 text-center py-4"
            >
                No fields match "{{ search }}"
            </p>
        </template>
    </div>
</template>
