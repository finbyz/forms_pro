<script setup lang="ts">
import { computed, ref } from "vue";
import { useEventListener } from "@vueuse/core";
import type { FormField } from "@/types/formfield";
import { useEditForm } from "@/stores/editForm";
import { writeDragPayload } from "@/utils/canvasDropTarget";
import FieldActions from "@/components/builder/FieldActions.vue";
import FieldRenderer from "@/components/builder/FieldRenderer.vue";

const props = defineProps<{
    field: FormField;
    isDraggingAnyField: boolean;
}>();

const editFormStore = useEditForm();

/**
 * The steps this field could move to -- every step except the one it is in.
 * Empty on a single-step form, which hides the control entirely.
 */
const stepOptions = computed(() => {
    const steps = editFormStore.sections ?? [];
    if (steps.length < 2) return [];

    const currentStep = steps.findIndex((s: { fields: FormField[] }) =>
        s.fields.includes(props.field)
    );

    return steps
        .map((step: { label: string }, index: number) => ({ step, index }))
        .filter(({ index }) => index !== currentStep)
        .map(({ step, index }) => ({
            label: step.label || `Step ${index + 1}`,
            onClick: () => editFormStore.moveFieldToStep(props.field, index),
        }));
});

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

// Enabled when there is a row directly above to join.
const canMergeUp = computed(() => {
    const row = props.field.row_index ?? 0;
    if (row <= 0) return false;
    return editFormStore.fields.some(
        (f: FormField) => f !== props.field && (f.row_index ?? 0) === row - 1
    );
});

function mergeWithAbove() {
    editFormStore.moveBesideAbove(props.field);
}

/**
 * The card is only draggable once the handle is held.
 *
 * `draggable` on a container swallows text selection and click-to-focus inside
 * it, so an input in the card would stop behaving like an input. Arming it on
 * the handle's pointerdown keeps both.
 */
const canDrag = ref(false);
const rootEl = ref<HTMLElement | null>(null);

useEventListener(document, "pointerdown", (event: PointerEvent) => {
    const handle = (event.target as HTMLElement | null)?.closest?.(".handle");
    canDrag.value = Boolean(handle && rootEl.value?.contains(handle));
});

useEventListener(document, "pointerup", () => {
    canDrag.value = false;
});

function onDragStart(event: DragEvent) {
    if (!canDrag.value || !props.field.fieldname) {
        event.preventDefault();
        return;
    }
    writeDragPayload(event, { source: "canvas", fieldname: props.field.fieldname });
    editFormStore.setDragging(true, props.field.fieldname);
}

function onDragEnd() {
    canDrag.value = false;
    editFormStore.setDragging(false);
}

function ejectToOwnRow() {
    editFormStore.insertNewRow(props.field, (props.field.row_index ?? 0) + 1);
}
</script>

<template>
    <!--
        Hover and press feedback are dropped while a drag is running. Nothing
        on the canvas moves during a drag any more, so this is no longer
        fixing a stutter -- it just stops every card the pointer crosses from
        lighting up on the way to the drop.
    -->
    <div
        ref="rootEl"
        :draggable="canDrag"
        @dragstart="onDragStart"
        @dragend="onDragEnd"
        class="relative flex-1 min-w-0 group cursor-pointer"
        :class="
            props.isDraggingAnyField
                ? 'fp-card-static'
                : 'transition-all duration-200 ease-out hover:shadow-sm active:scale-[0.99]'
        "
        data-form-builder-component="field-card"
        :data-field-label="props.field.label ?? ''"
        :data-field-name="props.field.fieldname ?? ''"
        :data-row-index="props.field.row_index ?? 0"
        :data-col-index="props.field.column_index ?? 0"
        :data-cell-index="props.field.cell_index ?? 0"
        @click="editFormStore.selectField(props.field)"
        :style="
            props.isDraggingAnyField
                ? undefined
                : 'transition-property: transform, box-shadow; transition-timing-function: ease-out;'
        "
    >
        <FieldActions
            :isSelected="editFormStore.selectedField === props.field"
            :isDraggingAnyField="props.isDraggingAnyField"
            :canEject="canEject"
            :stepOptions="stepOptions"
            :canMergeUp="canMergeUp"
            @remove="editFormStore.removeField(props.field)"
            @eject="ejectToOwnRow"
            @mergeUp="mergeWithAbove"
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
/* Nothing reacts to the pointer while a field is being dragged. */
.fp-card-static,
.fp-card-static * {
    transition: none !important;
    animation: none !important;
}

@media (prefers-reduced-motion: reduce) {
    .transition-all {
        transition: none !important;
    }
}
</style>
