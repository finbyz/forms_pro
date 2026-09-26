<script setup lang="ts">
import { useEditForm } from "@/stores/editForm";
import { FormControl } from "frappe-ui";
import { FormField } from "@/types/formfield";
import { FIELD_TYPE_DEFINITIONS } from "@/config/fieldTypes";
import { computed, ref, watch } from "vue";
import type { Component } from "vue";
import ConditionalLogicSection from "./ConditionalLogicSection.vue";

const activeTab = ref("General");
const tabs = ["General", "Validation", "Logic"];

const editFormStore = useEditForm();

type FieldProperty = {
    fieldname: keyof FormField;
    component: Component;
    props: Record<string, any>;
    visible?: boolean;
};

// Compute available target fields from the form's target DocType (e.g. Contact)
const targetFieldOptions = computed(() => {
    const list = [{ label: "(None / Custom field only)", value: "" }];
    const fields = editFormStore.doctypeFields || [];
    fields.forEach((f: any) => {
        list.push({
            label: `${f.label || f.fieldname} (${f.fieldname})`,
            value: f.fieldname,
        });
    });
    return list;
});

// Auto-sync source_type and mapping_type when target_field changes
watch(
    () => editFormStore.selectedField?.target_field,
    (newVal) => {
        if (!editFormStore.selectedField) return;
        if (newVal) {
            editFormStore.selectedField.source_type = "Target Field";
            if (!editFormStore.selectedField.mapping_type || editFormStore.selectedField.mapping_type === "No Target") {
                editFormStore.selectedField.mapping_type = "Direct";
            }
        }
    }
);

/** Field types whose `options` is a newline-separated list of choices. */
const OPTION_LIST_TYPES = new Set(["Select", "Multiselect"]);

const takesOptionList = computed(() =>
    OPTION_LIST_TYPES.has(String(editFormStore.selectedField?.fieldtype ?? ""))
);

const isLinkField = computed(
    () => String(editFormStore.selectedField?.fieldtype ?? "") === "Link"
);

const fieldProperties = computed(() => {
    const hasTargetDoctype = !!editFormStore.formData?.target_doctype;

    return [
        {
            fieldname: "label",
            component: FormControl,
            props: {
                type: "text",
                label: "Label",
                required: true,
                variant: "outline",
            },
        },
        {
            fieldname: "fieldname",
            component: FormControl,
            props: {
                type: "text",
                label: "Fieldname",
                required: true,
                variant: "outline",
            },
        },
        {
            fieldname: "placeholder",
            component: FormControl,
            props: {
                type: "text",
                label: "Placeholder Text",
                description: "Example text shown inside input (e.g. Beispiel: +41629199090).",
                variant: "outline",
            },
        },
        {
            fieldname: "fieldtype",
            component: FormControl,
            props: {
                type: "select",
                label: "Fieldtype",
                required: true,
                variant: "outline",
                options: FIELD_TYPE_DEFINITIONS.map((d) => d.name),
            },
        },
        {
            fieldname: "reqd",
            component: FormControl,
            props: {
                type: "checkbox",
                label: "Mandatory",
                description: "If enabled, the field becomes required and cannot be left blank.",
            },
        },
        {
            fieldname: "hidden",
            component: FormControl,
            props: {
                type: "checkbox",
                label: "Hidden",
                description: "If enabled, the field is hidden from the public form.",
            },
        },
        {
            fieldname: "read_only",
            component: FormControl,
            props: {
                type: "checkbox",
                label: "Read Only",
                description:
                    "Shown to the visitor but not editable. Set automatically when the "
                    + "DocType column is read only or fetched from another document.",
            },
        },
        {
            fieldname: "description",
            component: FormControl,
            props: {
                type: "textarea",
                label: "Help Text / Description",
                required: false,
                variant: "outline",
                rows: 4,
            },
        },
        {
            // Only the choice fields read `options` as a list. On a Link it is
            // the DocType being linked to, and on Data/Email/Number it means
            // nothing at all -- showing the same box everywhere invited people
            // to type options that were saved and then silently ignored.
            fieldname: "options",
            component: FormControl,
            visible: takesOptionList.value,
            props: {
                type: "textarea",
                label: "Options",
                description: "One option per line.",
                variant: "outline",
                rows: 4,
            },
        },
        {
            fieldname: "options",
            component: FormControl,
            visible: isLinkField.value,
            props: {
                type: "text",
                label: "Linked DocType",
                description: "Records of this DocType are offered in the dropdown.",
                variant: "outline",
            },
        },
        {
            fieldname: "default",
            component: FormControl,
            props: {
                type: "text",
                label: "Default / Pre-filled Value",
                description: "Default value submitted with the form (e.g. 'german').",
                variant: "outline",
            },
        },
        {
            fieldname: "conditional_logic",
            component: ConditionalLogicSection,
            props: {},
        },
        {
            fieldname: "target_field",
            component: FormControl,
            props: {
                type: "select",
                label: `Map to ${editFormStore.formData?.target_doctype || 'DocType'} Field`,
                description: "Link this form field to an existing field on the target DocType.",
                options: targetFieldOptions.value,
            },
            visible: hasTargetDoctype,
        },
        {
            fieldname: "source_type",
            component: FormControl,
            props: {
                type: "select",
                label: "Source Type",
                options: ["Target Field", "Form Field", "Presentation", "System"],
            },
        },
        {
            fieldname: "mapping_type",
            component: FormControl,
            props: {
                type: "select",
                label: "Mapping Type",
                options: [
                    "Direct",
                    "Constant",
                    "Transform",
                    "Child Table",
                    "Table MultiSelect",
                    "Attach",
                    "Attach Image",
                    "No Target",
                ],
            },
            visible: !!editFormStore.selectedField?.target_field,
        },
        {
            fieldname: "field_key",
            component: FormControl,
            props: {
                type: "text",
                label: "Field Key (Internal)",
                description: "Stable unique identifier used for form mapping.",
                disabled: true,
            },
        },
    ] as FieldProperty[];
});

const groupedProperties = computed(() => {
    return {
        General: fieldProperties.value.filter(p => ["label", "fieldname", "placeholder", "fieldtype", "description"].includes(p.fieldname)),
        Validation: fieldProperties.value.filter(p => ["reqd", "hidden", "read_only", "default", "options"].includes(p.fieldname)),
        Logic: fieldProperties.value.filter(p => ["target_field", "source_type", "mapping_type", "conditional_logic", "field_key"].includes(p.fieldname)),
    };
});
</script>
<template>
    <div
        class="flex flex-col w-full h-full bg-surface-base"
        data-form-builder-component="field-properties-form"
    >
        <!-- Tabs with clean Frappe friendly curves -->
        <div class="px-4 pt-3 pb-2 border-b border-outline-gray-1 bg-surface-base">
            <div class="flex items-center p-1 bg-surface-gray-2 rounded-xl border border-outline-gray-1/80 shadow-2xs">
                <button
                    v-for="tab in tabs"
                    :key="tab"
                    type="button"
                    class="flex-1 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 text-center"
                    :class="
                        activeTab === tab
                            ? 'bg-surface-white text-ink-gray-9 shadow-xs font-semibold border border-outline-gray-2/40'
                            : 'text-ink-gray-6 hover:text-ink-gray-9 hover:bg-surface-white/60'
                    "
                    @click="activeTab = tab"
                >
                    {{ tab }}
                </button>
            </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
            <template v-if="editFormStore.selectedField">
                <template v-for="property in groupedProperties[activeTab as keyof typeof groupedProperties]" :key="`${property.fieldname}-${property.props.label}`">
                    <component
                        v-if="property.visible !== false"
                        :is="property.component"
                        v-model="editFormStore.selectedField[property.fieldname]"
                        v-bind="property.props"
                    />
                </template>
            </template>
        </div>
    </div>
</template>
