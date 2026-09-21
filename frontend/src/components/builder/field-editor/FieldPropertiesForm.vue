<script setup lang="ts">
import { useEditForm } from "@/stores/editForm";
import { FormControl } from "frappe-ui";
import { FormField } from "@/types/formfield";
import { FIELD_TYPE_DEFINITIONS } from "@/config/fieldTypes";
import { computed, ref } from "vue";
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

const fieldProperties = computed(() => {
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
                description: "If enabled, the field is hidden from the form.",
            },
        },
        {
            fieldname: "description",
            component: FormControl,
            props: {
                type: "textarea",
                label: "Description",
                required: false,
                variant: "outline",
                rows: 5,
            },
        },
        {
            fieldname: "options",
            component: FormControl,
            props: {
                type: "textarea",
                label: "Options",
                description: "Enter the options for the field, one per line.",
                variant: "outline",
                rows: 5,
            },
        },
        {
            fieldname: "default",
            component: FormControl,
            props: {
                type: "text",
                label: "Default Value",
                description: "The default value for the field.",
                variant: "outline",
            },
        },
        {
            fieldname: "conditional_logic",
            component: ConditionalLogicSection,
            props: {},
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
        {
            fieldname: "source_type",
            component: FormControl,
            props: {
                type: "select",
                label: "Source Type",
                options: ["Custom", "Mapped"],
            },
        },
        {
            fieldname: "target_field",
            component: FormControl,
            props: {
                type: "text",
                label: "Target Field",
                description: "The fieldname in the target DocType this maps to.",
            },
            visible: editFormStore.selectedField?.source_type === "Mapped",
        },
        {
            fieldname: "mapping_type",
            component: FormControl,
            props: {
                type: "select",
                label: "Mapping Type",
                options: ["Direct", "Expression", "Webhook"],
            },
            visible: editFormStore.selectedField?.source_type === "Mapped",
        },
    ] as FieldProperty[];
});

const groupedProperties = computed(() => {
    return {
        General: fieldProperties.value.filter(p => ["label", "fieldname", "fieldtype", "description"].includes(p.fieldname)),
        Validation: fieldProperties.value.filter(p => ["reqd", "hidden", "default", "options"].includes(p.fieldname)),
        Logic: fieldProperties.value.filter(p => ["conditional_logic", "field_key", "source_type", "target_field", "mapping_type"].includes(p.fieldname)),
    };
});
</script>
<template>
    <div
        class="flex flex-col w-full h-full"
        data-form-builder-component="field-properties-form"
    >
        <!-- Tabs -->
        <div class="flex items-center w-full px-4 pt-4 border-b border-outline-gray-1 shrink-0 gap-4">
            <button
                v-for="tab in tabs"
                :key="tab"
                class="pb-2 text-sm font-medium transition-colors border-b-2 relative -mb-[1px]"
                :class="activeTab === tab ? 'border-ink-gray-9 text-ink-gray-9' : 'border-transparent text-ink-gray-5 hover:text-ink-gray-7'"
                @click="activeTab = tab"
            >
                {{ tab }}
            </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
            <template v-if="editFormStore.selectedField">
                <template v-for="property in groupedProperties[activeTab as keyof typeof groupedProperties]" :key="property.fieldname">
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
