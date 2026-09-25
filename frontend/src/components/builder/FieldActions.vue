<script setup lang="ts">
import { Button } from "frappe-ui";


defineProps<{
    isSelected: boolean;
    isDraggingAnyField: boolean;
    canEject: boolean;
    canMergeUp: boolean;
}>();

defineEmits<{
    (e: "remove"): void;
    (e: "eject"): void;
    (e: "mergeUp"): void;
}>();
</script>
<template>
    <!--
        Sits inside the card, top-right. It used to be `right-full`, i.e.
        entirely outside the card to the left, which the canvas clipped
        (overflow-y-auto forces overflow-x to auto) — so the actions were
        unreachable.
    -->
    <div
        :class="[
            'absolute right-2 top-2 z-10 flex flex-row items-center rounded border border-outline-gray-2 bg-surface-white shadow-sm px-1 h-8 transition-all duration-200 ease-out',
            isSelected
                ? 'opacity-100 scale-100'
                : isDraggingAnyField
                ? 'opacity-0 scale-90 pointer-events-none'
                : 'opacity-0 scale-90 group-hover:opacity-100 group-hover:scale-100',
        ]"
    >
        <Button
            v-if="canMergeUp"
            size="sm"
            icon="columns"
            variant="ghost"
            @click.stop="$emit('mergeUp')"
            tooltip="Place beside the field above (make a column)"
            data-form-builder-component="merge-up-button"
        />
        <Button
            v-if="canEject"
            size="sm"
            icon="square"
            variant="ghost"
            @click.stop="$emit('eject')"
            tooltip="Move to own row"
            data-form-builder-component="eject-button"
        />
        <Button
            size="sm"
            icon="trash-2"
            variant="ghost"
            @click.stop="$emit('remove')"
            tooltip="Remove this field"
        />
        <Button
            class="handle"
            size="sm"
            icon="move"
            variant="ghost"
            tooltip="Drag to move"
        />
    </div>
</template>

<style scoped>
.handle {
    cursor: grab;
}

.handle:active {
    cursor: grabbing;
}
</style>
