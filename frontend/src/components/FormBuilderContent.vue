<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from "vue";
import { LoadingIndicator } from "frappe-ui";

// Same reason as the field registry: keep ProseMirror out of the eager graph.
const TextEditor = defineAsyncComponent(() => import("@/components/fields/TextEditor.vue"));
import { onClickOutside, useEventListener } from "@vueuse/core";

import { useEditForm } from "@/stores/editForm";
import { useGroupedRows } from "@/composables/useGroupedRows";
import type { FormField } from "@/types/formfield";
import FieldCard from "@/components/builder/FieldCard.vue";
import DropIndicator from "@/components/builder/DropIndicator.vue";
import { resolveDropTarget, type DropTarget } from "@/utils/dropGeometry";
import { readDragPayload, readRows, type DragPayload } from "@/utils/canvasDropTarget";
import SectionNavBar from "@/components/builder/SectionNavBar.vue";
import SuccessCanvas from "@/components/studio/success/SuccessCanvas.vue";

const editFormStore = useEditForm();

const fieldContentRef = ref<HTMLElement | null>(null);
const isDraggingField = computed(() => editFormStore.isDraggingField);

/**
 * Where the dragged field would land, recomputed as the pointer moves.
 *
 * This is the only thing that changes during a drag. The canvas itself is
 * untouched until the drop, which is what keeps it still.
 */
const dropTarget = ref<DropTarget | null>(null);

function resetDragState() {
    editFormStore.setDragging(false);
    dropTarget.value = null;
}

useEventListener(document, "pointerup", () => {
    if (isDraggingField.value) resetDragState();
});
useEventListener(document, "dragend", () => {
    if (isDraggingField.value) resetDragState();
});

const groupedRows = useGroupedRows(
    computed(() =>
        editFormStore.isMultiSection ? editFormStore.activeSectionFields : editFormStore.fields
    )
);

/**
 * A field's identity, not its position.
 *
 * This used to be `row-column-cell`, which changes the moment a field is
 * dragged anywhere -- so Vue treated every field that shifted as a different
 * field, destroyed its component and built a new one mid-drag. That is the
 * flicker: the card under the cursor and every card it passes are being torn
 * down and recreated instead of moved. Keyed by fieldname, Vue moves the
 * existing DOM node and the drag stays still.
 */
function fieldKey(field: FormField): string {
    return field.fieldname || field.field_key || `${field.row_index}-${field.column_index}-${field.cell_index}`;
}

function rowIndexOf(row: FormField[][], rIdx: number): number {
    return row[0]?.[0]?.row_index ?? rIdx;
}

function colIndexOf(col: FormField[], cIdx: number): number {
    return col[0]?.column_index ?? cIdx;
}

/** The field a canvas drag is carrying, or null while dragging in a new one. */
function fieldFromPayload(payload: DragPayload): FormField | null {
    if (payload.source === "canvas") {
        return (
            editFormStore.fields.find((f: FormField) => f.fieldname === payload.fieldname) ?? null
        );
    }
    if (payload.source === "palette") return editFormStore.materializeNewField(payload.fieldtype);
    if (payload.source === "doctype") {
        const available = editFormStore.doctypeFields ?? [];
        const source = available.find((f: any) => f.fieldname === payload.fieldname);
        return source ? editFormStore.materializeDoctypeField(source) : null;
    }
    return null;
}

/**
 * Work out where the field would land and move the indicator there.
 *
 * Nothing is written to the form here. Measuring is all that happens on a
 * pointer move, which is the whole point of doing it this way.
 */
function onCanvasDragOver(event: DragEvent) {
    if (!isDraggingField.value) return;
    event.preventDefault();

    const canvas = fieldContentRef.value;
    if (!canvas) return;

    const rows = readRows(canvas, editFormStore.draggingFieldname ?? undefined);
    dropTarget.value = resolveDropTarget(rows, event.clientX, event.clientY);
}

function onCanvasDragLeave(event: DragEvent) {
    // `relatedTarget` is what the pointer moved onto; staying inside the canvas
    // fires dragleave for every child crossed, which would flicker the line.
    const leaving = event.relatedTarget as Node | null;
    if (leaving && fieldContentRef.value?.contains(leaving)) return;
    dropTarget.value = null;
}

function onCanvasDrop(event: DragEvent) {
    event.preventDefault();

    const payload = readDragPayload(event);
    const target = dropTarget.value;
    resetDragState();
    if (!payload) return;

    const field = fieldFromPayload(payload);
    if (!field) return;

    // An empty canvas has no geometry to read, so the first field starts row 0.
    if (!target) {
        if (!editFormStore.fields.length) editFormStore.insertNewRow(field, 0);
        return;
    }

    if (target.kind === "row") {
        editFormStore.insertNewRow(field, target.rowIndex);
    } else if (target.kind === "column") {
        editFormStore.moveField(field, target.rowIndex, target.columnIndex ?? 0);
    } else {
        editFormStore.insertCell(
            field,
            target.rowIndex,
            target.columnIndex ?? 0,
            target.cellIndex ?? 0
        );
    }
}

// Function to check if an element is a dropdown/popover (including portals)
const isDropdownOrPopover = (element: Element | null): boolean => {
    if (!element) return false;

    let current: Element | null = element;
    while (current && current !== document.body) {
        if (
            current.hasAttribute("role") &&
            (current.getAttribute("role") === "listbox" ||
                current.getAttribute("role") === "option" ||
                current.getAttribute("role") === "combobox")
        ) {
            return true;
        }

        if (current.hasAttribute("data-headlessui-state") || current.id?.includes("headlessui")) {
            return true;
        }

        if (
            current.hasAttribute("data-radix-popper-content-wrapper") ||
            current.id?.startsWith("radix") ||
            current.hasAttribute("data-radix")
        ) {
            return true;
        }

        const classList = current.classList;
        if (
            classList.contains("dropdown-menu") ||
            classList.contains("combobox-options") ||
            classList.contains("popover-content") ||
            current.hasAttribute("data-popover")
        ) {
            return true;
        }

        current = current.parentElement;
    }

    return false;
};

useEventListener("keydown", (event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "s") {
        event.preventDefault();
        editFormStore.save();
    }
});

onClickOutside(fieldContentRef, (event) => {
    const target = event.target as Element;
    const isFormBuilderComponent =
        target.closest("[data-form-builder-component]") ||
        target.closest(".field-editor-sidebar") ||
        target.closest(".form-builder-sidebar") ||
        target.closest(".form-builder-header");

    const isDropdownElement = isDropdownOrPopover(target);

    const hasOpenDropdown = !!(
        document.querySelector('[role="listbox"]:not([hidden]):not([style*="display: none"])') ||
        document.querySelector('[role="combobox"][aria-expanded="true"]') ||
        document.querySelector('[data-headlessui-state="open"]') ||
        document.querySelector('[aria-expanded="true"][role="combobox"]')
    );

    const activeElement = document.activeElement;
    const isActiveElementInSidebar = activeElement
        ? !!(
              activeElement.closest(".field-editor-sidebar") ||
              activeElement.closest('[data-form-builder-component="field-editor-sidebar"]') ||
              activeElement.closest('[data-form-builder-component="field-properties-form"]')
          )
        : false;

    if (
        !isFormBuilderComponent &&
        !isDropdownElement &&
        !hasOpenDropdown &&
        !isActiveElementInSidebar
    ) {
        editFormStore.selectField(null);
    }
});
</script>

<template>
    <div class="flex flex-col flex-1 min-w-0 min-h-0 overflow-hidden bg-surface-gray-1">
        <div v-if="editFormStore.isLoading" class="flex items-center justify-center h-full">
            <LoadingIndicator />
        </div>
        <template v-else>
            <!-- Sticky section nav bar -->
            <div class="shrink-0 flex justify-center w-full bg-surface-gray-1 border-b border-outline-gray-1 px-6 py-1">
                <SectionNavBar v-if="editFormStore.formData" class="max-w-[960px] w-full" />
            </div>

            <!-- Scrollable canvas -->
            <div class="flex-1 overflow-y-auto">
                <div v-if="editFormStore.formData && editFormStore.activeSectionIndex === 'success'" class="h-full w-full bg-white">
                    <SuccessCanvas />
                </div>

                <!--
                    One drop surface for the whole canvas, rather than a
                    SortableJS list per column and per gap. Dragover only
                    measures and moves the indicator; the form is rearranged
                    once, on drop.
                -->
                <div
                    v-else-if="editFormStore.formData"
                    ref="fieldContentRef"
                    class="max-w-[960px] mx-auto bg-surface-base border border-outline-gray-1 rounded-6 shadow-sm my-6 mb-24"
                    @dragover="onCanvasDragOver"
                    @dragleave="onCanvasDragLeave"
                    @drop="onCanvasDrop"
                >
                    <div class="p-8">
                        <div class="flex flex-col gap-3 mb-8">
                            <input
                                type="text"
                                class="outline-none bg-transparent border-none text-2xl-semibold text-ink-gray-9 focus:ring-0 p-0 placeholder:text-ink-gray-4"
                                placeholder="Untitled Form"
                                v-model="editFormStore.formData.title"
                            />
                            <TextEditor
                                :content="editFormStore.formData.description"
                                editor-class="h-fit !w-full form-description text-ink-gray-7"
                                placeholder="Write a description for your form"
                                @change="(value: string) => (editFormStore.formData.description = value)"
                                :starterkit-options="{
                                    heading: {
                                        levels: [1, 2, 3, 4, 5, 6],
                                    },
                                }"
                                :bubble-menu="true"
                            />
                        </div>
                        <hr class="border-outline-gray-1 -mx-8 mb-8" />
                        <div
                            v-if="groupedRows.length === 0"
                            data-form-builder-component="empty-canvas-drop-zone"
                            :class="[
                                'flex flex-col gap-4 p-8 min-h-48 items-center justify-center rounded-6 text-center border-2 border-dashed transition-colors duration-150 ease-out motion-reduce:transition-none',
                                isDraggingField
                                    ? 'bg-surface-blue-1 border-outline-blue-2'
                                    : 'bg-surface-gray-1 border-outline-gray-2',
                            ]"
                        >
                            <p class="text-sm-medium text-ink-gray-6">Add fields to design your form</p>
                            <p class="text-xs text-ink-gray-5">
                                Drag fields in from the sidebar, or click the + on one
                            </p>
                        </div>
                        <div class="flex flex-col" v-else>
                            <template v-for="(row, rIdx) in groupedRows" :key="rowIndexOf(row, rIdx)">
                                <div
                                    class="flex flex-row items-stretch gap-5 mb-5 last:mb-0"
                                    data-form-builder-component="form-row"
                                    :data-row-index="rowIndexOf(row, rIdx)"
                                >
                                    <div
                                        v-for="(col, cIdx) in row"
                                        :key="`${rowIndexOf(row, rIdx)}-${colIndexOf(col, cIdx)}`"
                                        data-form-builder-component="cell-column"
                                        :data-row-index="rowIndexOf(row, rIdx)"
                                        :data-col-index="colIndexOf(col, cIdx)"
                                        class="flex flex-col gap-5 flex-1 min-w-0"
                                    >
                                        <FieldCard
                                            v-for="field in col"
                                            :key="fieldKey(field)"
                                            :field="field"
                                            :isDraggingAnyField="isDraggingField"
                                        />
                                    </div>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>
            </div>
        </template>

        <DropIndicator :indicator="dropTarget?.indicator ?? null" />
    </div>
</template>
