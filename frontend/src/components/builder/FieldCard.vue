<script setup lang="ts">
import { computed } from "vue";
import type { FormField } from "@/types/formfield";
import { useEditForm } from "@/stores/editForm";
import FieldActions from "@/components/builder/FieldActions.vue";
import FieldRenderer from "@/components/builder/FieldRenderer.vue";

const props = defineProps<{
    field: FormField;
    isDraggingAnyField: boolean;
}>();

const editFormStore = useEditForm();

// Eject = "Move to own row". Available whenever the row holds more than one
// cell — that is, more than one column OR more than one stacked cell within
// a single column. (Variable was previously named `isMultiColumn`, which
// understated the stacked-cell case.)
const canEject = computed(
    () =>
        editFormStore.fields.filter(
            (f: FormField) => (f.row_index ?? 0) === (props.field.row_index ?? 0)
        ).length > 1
);

function ejectToOwnRow() {
    editFormStore.insertNewRow(props.field, (props.field.row_index ?? 0) + 1);
}
</script>

<template>
    <div
        class="relative flex-1 min-w-0 transition-all duration-200 ease-out group cursor-pointer hover:shadow-sm active:scale-[0.99]"
        data-form-builder-component="field-card"
        :data-field-label="props.field.label ?? ''"
        :data-field-name="props.field.fieldname ?? ''"
        :data-row-index="props.field.row_index ?? 0"
        :data-col-index="props.field.column_index ?? 0"
        :data-cell-index="props.field.cell_index ?? 0"
        @click="editFormStore.selectField(props.field)"
        style="transition-property: transform, box-shadow; transition-timing-function: ease-out;"
    >
        <FieldActions
            :isSelected="editFormStore.selectedField === props.field"
            :isDraggingAnyField="props.isDraggingAnyField"
            :canEject="canEject"
            @remove="editFormStore.removeField(props.field)"
            @eject="ejectToOwnRow"
        />
        <FieldRenderer
            :field="props.field"
            :inEditMode="true"
            @update:field="
                (updated: FormField) => editFormStore.updateField(props.field, updated)
            "
        />
    </div>
</template>

<style scoped>
@media (prefers-reduced-motion: reduce) {
    .transition-all {
        transition: none !important;
    }
}
</style>
