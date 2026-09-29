<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from "vue";
import { LoadingIndicator } from "frappe-ui";

// Same reason as the field registry: keep ProseMirror out of the eager graph.
const TextEditor = defineAsyncComponent(() => import("@/components/fields/TextEditor.vue"));
import { onClickOutside, useEventListener } from "@vueuse/core";
import draggableComponent from "vuedraggable";

import { useEditForm } from "@/stores/editForm";
import { useGroupedRows } from "@/composables/useGroupedRows";
import type { FormField } from "@/types/formfield";
import FieldCard from "@/components/builder/FieldCard.vue";
import RowDropZone from "@/components/builder/RowDropZone.vue";
import ColumnDropZone from "@/components/builder/ColumnDropZone.vue";
import SectionNavBar from "@/components/builder/SectionNavBar.vue";
import SuccessCanvas from "@/components/studio/success/SuccessCanvas.vue";

const editFormStore = useEditForm();

const fieldContentRef = ref<HTMLElement | null>(null);
const isDraggingField = computed(() => editFormStore.isDraggingField);
// SortableJS needs a backing list for the empty-canvas drop target.
const emptyBuffer = ref<FormField[]>([]);

function resetDragState() {
    editFormStore.setDragging(false);
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

/**
 * A drop can carry either an existing form field (a move) or a clone of a
 * DocType field from the sidebar (a new field). The store's positioning
 * helpers only accept fields already in doc.fields, so materialize first.
 */
function resolveDropped(element: any): FormField | null {
    if (!element) return null;
    if (editFormStore.isFormField(element)) return element;
    if (element.__fromDoctype) return editFormStore.materializeDoctypeField(element);
    if (element.__newFieldtype) return editFormStore.materializeNewField(element.__newFieldtype);
    return null;
}

function onEmptyCanvasDrop(evt: any) {
    if (!evt.added) return;
    const field = resolveDropped(evt.added.element);
    if (field) editFormStore.insertNewRow(field, 0);
    emptyBuffer.value = [];
    resetDragState();
}

function onCellChange(evt: any, rowIndex: number, colIndex: number) {
    if (evt.moved) {
        // Reorder cells within same column: renumber cell_index by new position
        const { element, newIndex } = evt.moved;
        const cells: FormField[] = editFormStore.fields
            .filter(
                (f: FormField) =>
                    (f.row_index ?? 0) === rowIndex && (f.column_index ?? 0) === colIndex
            )
            .sort((a: FormField, b: FormField) => (a.cell_index ?? 0) - (b.cell_index ?? 0));
        const oldIdx = cells.indexOf(element);
        if (oldIdx === -1) return;
        cells.splice(oldIdx, 1);
        cells.splice(newIndex, 0, element);
        cells.forEach((f: FormField, i: number) => {
            f.cell_index = i;
        });
    } else if (evt.added) {
        // Field dropped into this column from elsewhere — stack into column at cell index
        const field = resolveDropped(evt.added.element);
        if (field) editFormStore.insertCell(field, rowIndex, colIndex, evt.added.newIndex);
        resetDragState();
    }
    // evt.removed: no-op — target column's evt.added owns the move
}

function onColumnZoneDrop(dropped: FormField, atRow: number, atCol: number) {
    const field = resolveDropped(dropped);
    if (field) editFormStore.moveField(field, atRow, atCol);
    resetDragState();
}

function onRowZoneDrop(dropped: FormField, atRow: number) {
    const field = resolveDropped(dropped);
    if (field) editFormStore.insertNewRow(field, atRow);
    resetDragState();
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

                <div
                    v-else-if="editFormStore.formData"
                    ref="fieldContentRef"
                    class="max-w-[960px] mx-auto bg-surface-base border border-outline-gray-1 rounded-6 shadow-sm my-6 mb-24"
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
                        <draggableComponent
                            v-if="groupedRows.length === 0"
                            :list="emptyBuffer"
                            :group="{ name: 'fields', put: true, pull: false }"
                            item-key="fieldname"
                            tag="div"
                            data-form-builder-component="empty-canvas-drop-zone"
                            :class="[
                                'flex flex-col gap-4 p-8 min-h-48 items-center justify-center rounded-6 text-center border-2 border-dashed transition-colors duration-150 ease-out motion-reduce:transition-none',
                                isDraggingField
                                    ? 'bg-surface-blue-1 border-outline-blue-2'
                                    : 'bg-surface-gray-1 border-outline-gray-2',
                            ]"
                            @change="onEmptyCanvasDrop"
                        >
                            <template #header>
                                <p class="text-sm-medium text-ink-gray-6">Add fields to design your form</p>
                                <p class="text-xs text-ink-gray-5">
                                    Drag fields in from the sidebar, or click the + on one
                                </p>
                            </template>
                            <template #item="{}"></template>
                        </draggableComponent>
                        <div class="flex flex-col" v-else>
                            <!--
                                The drop zones exist only while something is
                                being dragged. Each one is its own SortableJS
                                instance, and the row zones each run a
                                MutationObserver, so on a long form they added
                                up to well over a hundred live instances
                                sitting idle -- paid for on every scroll and
                                every click. `isDraggingField` is set on drag
                                start, before the first dragover, so they are
                                mounted by the time a drop could land.
                            -->
                            <template v-for="(row, rIdx) in groupedRows" :key="rowIndexOf(row, rIdx)">
                                <RowDropZone
                                    v-if="isDraggingField"
                                    :atRow="rowIndexOf(row, rIdx)"
                                    :isDragging="isDraggingField"
                                    @drop="onRowZoneDrop"
                                />
                                <div
                                    class="flex flex-row items-stretch gap-5 mb-5 last:mb-0"
                                    data-form-builder-component="form-row"
                                    :data-row-index="rowIndexOf(row, rIdx)"
                                >
                                    <template
                                        v-for="(col, cIdx) in row"
                                        :key="`${rowIndexOf(row, rIdx)}-${colIndexOf(col, cIdx)}`"
                                    >
                                        <ColumnDropZone
                                            v-if="isDraggingField"
                                            :atRow="rowIndexOf(row, rIdx)"
                                            :atCol="colIndexOf(col, cIdx)"
                                            :isDragging="isDraggingField"
                                            @drop="onColumnZoneDrop"
                                        />
                                        <draggableComponent
                                            :list="[...col]"
                                            :group="{ name: 'fields' }"
                                            :item-key="fieldKey"
                                            :animation="150"
                                            handle=".handle"
                                            ghost-class="fp-drag-ghost"
                                            chosen-class="fp-drag-chosen"
                                            tag="div"
                                            direction="vertical"
                                            :swap-threshold="0.65"
                                            :invert-swap="true"
                                            :empty-insert-threshold="28"
                                            :scroll-sensitivity="90"
                                            :scroll-speed="18"
                                            :bubble-scroll="true"
                                            data-form-builder-component="cell-column"
                                            :data-row-index="rowIndexOf(row, rIdx)"
                                            :data-col-index="colIndexOf(col, cIdx)"
                                            class="flex flex-col gap-5 flex-1 min-w-0"
                                            @change="
                                            (evt: any) =>
                                                onCellChange(
                                                    evt,
                                                    rowIndexOf(row, rIdx),
                                                    colIndexOf(col, cIdx)
                                                )
                                        "
                                            @start="editFormStore.setDragging(true)"
                                            @end="editFormStore.setDragging(false)"
                                        >
                                            <template #item="{ element: field }">
                                                <FieldCard
                                                    :field="field"
                                                    :isDraggingAnyField="isDraggingField"
                                                />
                                            </template>
                                        </draggableComponent>
                                    </template>
                                    <ColumnDropZone
                                        v-if="isDraggingField"
                                        :atRow="rowIndexOf(row, rIdx)"
                                        :atCol="row.length"
                                        :isDragging="isDraggingField"
                                        @drop="onColumnZoneDrop"
                                    />
                                </div>
                                <RowDropZone
                                    v-if="isDraggingField && rIdx === groupedRows.length - 1"
                                    :atRow="rowIndexOf(row, rIdx) + 1"
                                    :isDragging="isDraggingField"
                                    @drop="onRowZoneDrop"
                                />
                            </template>
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </div>
</template>
