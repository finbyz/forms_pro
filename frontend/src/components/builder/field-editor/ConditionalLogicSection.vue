<script setup lang="ts">
import { useEditForm } from "@/stores/editForm";
import { ref, watch, computed } from "vue";
import {
    ConditionalLogic,
    ConditionalOperators,
    type Condition,
    Actions,
} from "@/types/conditional-render.types";
import { FormControl, Popover, Button } from "frappe-ui";

import type { FormField } from "@/types/formfield";
import { getFieldnamesInSection } from "@/utils/conditionals";

const editFormStore = useEditForm();

const conditionalLogic = ref<ConditionalLogic | null>(null);
const isUpdatingFromStore = ref(false);

// Helper function to parse conditional_logic value
const parseConditionalLogic = (
    value: string | ConditionalLogic | undefined
): ConditionalLogic | null => {
    if (!value) return null;
    if (typeof value === "string") {
        try {
            return JSON.parse(value) as ConditionalLogic;
        } catch (e) {
            console.error("Failed to parse conditional_logic:", e);
            return null;
        }
    }
    return value as ConditionalLogic;
};

// Helper function to stringify conditionalLogic
const stringifyConditionalLogic = (value: ConditionalLogic | null): string | undefined => {
    if (!value) return undefined;
    return JSON.stringify(value);
};

// Watch for changes in selectedField or its conditional_logic from external sources
watch(
    () => [editFormStore.selectedField?.fieldname, editFormStore.selectedField?.conditional_logic],
    () => {
        // Prevent infinite loop - don't update if we're the ones updating the store
        if (isUpdatingFromStore.value) return;

        const parsed = parseConditionalLogic(editFormStore.selectedField?.conditional_logic);
        conditionalLogic.value = parsed;
    },
    { immediate: true }
);

// Watch conditionalLogic and update selectedField.conditional_logic whenever it changes
watch(
    conditionalLogic,
    (newValue) => {
        if (!editFormStore.selectedField) return;

        // Set flag to prevent infinite loop
        isUpdatingFromStore.value = true;

        try {
            if (!conditionalLogic.value || conditionalLogic.value.conditions.length === 0) {
                editFormStore.selectedField.conditional_logic = "";
            } else {
                editFormStore.selectedField.conditional_logic =
                    stringifyConditionalLogic(newValue);
            }
        } finally {
            // Reset flag after a microtask to allow the other watcher to process
            setTimeout(() => {
                isUpdatingFromStore.value = false;
            }, 0);
        }
    },
    { deep: true }
);

const addCondition = () => {
    if (!conditionalLogic.value) {
        conditionalLogic.value = {
            conditions: [],
            action: Actions.ShowField,
            target_field: editFormStore.selectedField?.fieldname || null,
        } as ConditionalLogic;
    } else if (!conditionalLogic.value.target_field && editFormStore.selectedField?.fieldname) {
        conditionalLogic.value.target_field = editFormStore.selectedField.fieldname;
    }

    conditionalLogic.value.conditions.push({
        fieldname: "",
        operator: ConditionalOperators.Is,
        value: "",
    } as Condition);
};

const removeCondition = (index: number) => {
    if (!conditionalLogic.value) return;
    conditionalLogic.value.conditions.splice(index, 1);
};

const isSeparator = (field: FormField) =>
    field.fieldtype === "Page Break" ||
    (field as any).fieldtype === "Tab Break" ||
    (field as any).fieldtype === "Section Break";

const toOption = (field: FormField) => ({
    label: `${isSeparator(field) ? "[Step / Section] " : ""}${field.label || field.fieldname} (${field.fieldname})`,
    value: field.fieldname,
});

const availableFieldOptions = computed(() => editFormStore.fields.map(toOption));

const triggerFieldnames = computed(() =>
    (conditionalLogic.value?.conditions || []).map((c) => c.fieldname).filter(Boolean)
);

/**
 * A step may not be the target of a rule triggered from inside itself: hiding
 * the step would hide the question that drives it, and the fields around the
 * trigger get swept along with no sign of why. Those steps are left out here so
 * the rule cannot be built in the first place.
 */
const targetFieldOptions = computed(() =>
    editFormStore.fields
        .filter(
            (field: FormField) =>
                !isSeparator(field) ||
                !getFieldnamesInSection(field.fieldname, editFormStore.fields).some((name) =>
                    triggerFieldnames.value.includes(name)
                )
        )
        .map(toOption)
);

// True for a rule saved before that restriction existed: its target is gone
// from the list, so the select shows blank until a real target is chosen.
const hasStaleTarget = computed(() => {
    const target = conditionalLogic.value?.target_field;
    if (!target || Array.isArray(target)) return false;
    return !targetFieldOptions.value.some((o) => o.value === target);
});

const operatorOptions = computed(() => {
    return Object.values(ConditionalOperators).map((operator) => ({
        label: operator,
        value: operator,
    }));
});

const actionOptions = computed(() => {
    return Object.values(Actions).map((action) => ({
        label: action,
        value: action,
    }));
});

const showValueInput = (operator: ConditionalOperators) => {
    return (
        operator !== ConditionalOperators.IsEmpty &&
        operator !== ConditionalOperators.IsNotEmpty &&
        operator !== ConditionalOperators.IsSet
    );
};

const getConditionField = (fieldname: string): FormField | undefined => {
    return editFormStore.fields.find((f: FormField) => f.fieldname === fieldname);
};

const getConditionFieldOptions = (fieldname: string) => {
    const field = getConditionField(fieldname);
    if (!field) return null;

    if (field.fieldtype === "Check" || field.fieldtype === "Checkbox" || field.fieldtype === "Switch") {
        return [
            { label: "Checked (1)", value: "1" },
            { label: "Unchecked (0)", value: "0" },
        ];
    }

    if (field.fieldtype === "Select" && field.options) {
        const lines = typeof field.options === "string" ? field.options.split("\n") : [];
        const opts = lines.map((line: string) => line.trim()).filter(Boolean);
        if (opts.length > 0) {
            return opts.map((opt: string) => ({ label: opt, value: opt }));
        }
    }

    return null;
};
</script>
<template>
    <div class="flex flex-col gap-2">
        <label class="block text-xs text-ink-gray-5">Conditional Logic</label>
        <div
            v-if="conditionalLogic && conditionalLogic.conditions.length > 0"
            class="p-3 bg-surface-gray-1 border rounded flex flex-col gap-4"
        >
            <div
                v-for="(condition, index) in conditionalLogic?.conditions"
                :key="index"
                class="flex flex-col gap-2 p-2.5 bg-surface-white border rounded shadow-xs"
            >
                <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-2 text-ink-gray-7 text-xs font-medium">
                        <lucide-workflow class="w-3.5 h-3.5" aria-hidden="true" />
                        <span>{{ index === 0 ? "When" : "And" }}</span>
                    </div>
                    <Popover>
                        <template #target="{ togglePopover }">
                            <Button
                                variant="ghost"
                                size="sm"
                                @click="togglePopover"
                                :icon="'more-vertical'"
                                tooltip="Actions"
                            />
                        </template>
                        <template #body-main>
                            <div
                                class="flex flex-col gap-2 p-2 bg-surface-white rounded field-editor-sidebar"
                            >
                                <Button
                                    variant="ghost"
                                    theme="red"
                                    size="sm"
                                    @click="removeCondition(index)"
                                    :icon-left="'trash'"
                                    label="Remove"
                                    tooltip="Remove Condition"
                                />
                            </div>
                        </template>
                    </Popover>
                </div>
                <FormControl
                    type="select"
                    placeholder="Select Field"
                    variant="outline"
                    :options="availableFieldOptions"
                    v-model="condition.fieldname"
                />
                <FormControl
                    type="select"
                    placeholder="Select Operator"
                    variant="outline"
                    :options="operatorOptions"
                    v-model="condition.operator"
                />
                <FormControl
                    v-if="showValueInput(condition.operator) && getConditionFieldOptions(condition.fieldname)"
                    type="select"
                    placeholder="Select Value"
                    variant="outline"
                    :options="getConditionFieldOptions(condition.fieldname)!"
                    v-model="condition.value"
                />
                <FormControl
                    v-else-if="showValueInput(condition.operator)"
                    type="text"
                    placeholder="Value"
                    variant="outline"
                    v-model="condition.value"
                />
            </div>

            <Button
                variant="subtle"
                size="sm"
                class="self-start text-xs"
                @click="addCondition"
                :icon-left="'plus'"
                label="Add Condition"
            />

            <!-- Actions -->
            <div class="border-t pt-3 flex flex-col gap-2">
                <div class="flex items-center gap-2 text-ink-gray-7 text-xs font-medium">
                    <lucide-zap class="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Then</span>
                </div>
                <FormControl
                    type="select"
                    placeholder="Select Action"
                    variant="outline"
                    :options="actionOptions"
                    v-model="conditionalLogic.action"
                />
                <FormControl
                    type="select"
                    placeholder="Select Target Field"
                    variant="outline"
                    :options="targetFieldOptions"
                    v-model="conditionalLogic.target_field"
                />
                <p v-if="hasStaleTarget" class="text-xs text-ink-red-4">
                    This rule pointed at the step it sits in, so it affected fields it was
                    never aimed at. Pick the field it should control.
                </p>
            </div>
        </div>
        <Button
            v-if="!conditionalLogic || conditionalLogic?.conditions.length === 0"
            variant="outline"
            size="sm"
            @click="addCondition"
            :icon-left="'plus'"
            label="Add Rule"
            tooltip="Add Condition"
        />
    </div>
</template>
