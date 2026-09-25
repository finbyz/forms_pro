<script setup lang="ts">
import { ref, computed, nextTick } from "vue";
import { TextInput, FeatherIcon } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import { dialog } from "@/utils/dialog";

const store = useEditForm();

const sectionCount = computed(() => store.sections.length);
const editingIndex = ref<number | null>(null);
const editInput = ref<InstanceType<typeof TextInput> | null>(null);
const editValue = ref("");
const cancelRename = ref(false);

function startRename(index: number) {
    cancelRename.value = false;
    editValue.value = store.sections[index].label;
    editingIndex.value = index;
    nextTick(() => editInput.value?.el?.select());
}

function finishRename(index: number) {
    if (cancelRename.value) {
        cancelRename.value = false;
        editingIndex.value = null;
        return;
    }
    if (editValue.value.trim()) {
        store.renameStep(index, editValue.value.trim());
    }
    editingIndex.value = null;
}

function onEditKeydown(event: KeyboardEvent, index: number) {
    if (event.key === "Enter") {
        finishRename(index);
    } else if (event.key === "Escape") {
        cancelRename.value = true;
        editingIndex.value = null;
    }
}

function confirmRemoveSection(index: number) {
    const section = store.sections[index];
    const hasFields = section.fields.length > 0;

    if (!hasFields) {
        store.removeStepKeepFields(index);
        return;
    }

    dialog.show({
        title: `Remove "${section.label}"?`,
        message: `This step has ${section.fields.length} field(s). What would you like to do?`,
        actions: [
            {
                label: "Cancel",
                variant: "outline",
                onClick: () => dialog.close(false),
            },
            {
                label: "Move fields to previous step",
                variant: "subtle",
                onClick: () => {
                    store.removeStepKeepFields(index);
                    dialog.close(true);
                },
            },
            {
                label: "Remove step and fields",
                variant: "solid",
                theme: "red",
                onClick: () => {
                    store.removeStepWithFields(index);
                    dialog.close(true);
                },
            },
        ],
    });
}
</script>

<template>
    <nav aria-label="Form steps" class="flex items-center gap-2 px-3 py-2 flex-wrap">
        <div class="inline-flex items-center gap-1 p-1 bg-surface-gray-2 rounded-xl border border-outline-gray-1/80 shadow-2xs">
            <template v-for="(section, idx) in store.sections" :key="section.label">
                <button
                    v-if="editingIndex !== idx"
                    type="button"
                    :aria-current="idx === store.activeSectionIndex ? 'true' : undefined"
                    @click="store.activeSectionIndex = idx"
                    @dblclick="startRename(idx)"
                    :title="'Double-click to rename ' + section.label"
                    class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150"
                    :class="
                        idx === store.activeSectionIndex
                            ? 'bg-surface-white text-ink-gray-9 shadow-xs font-semibold border border-outline-gray-2/40'
                            : 'text-ink-gray-6 hover:text-ink-gray-9 hover:bg-surface-white/60'
                    "
                >
                    <span>{{ section.label }}</span>
                    <button
                        v-if="idx > 0 && store.sections.length > 1"
                        type="button"
                        aria-label="Remove step"
                        class="p-0.5 -mr-1 rounded-md text-ink-gray-4 hover:text-ink-red-6 hover:bg-surface-gray-3 transition-colors"
                        @click.stop="confirmRemoveSection(idx)"
                    >
                        <FeatherIcon name="x" class="size-3" />
                    </button>
                </button>
                <TextInput
                    v-else
                    ref="editInput"
                    v-model="editValue"
                    size="sm"
                    variant="outline"
                    @blur="finishRename(idx)"
                    @keydown="onEditKeydown($event, idx)"
                    class="w-28"
                />
            </template>

            <!-- Add Step button -->
            <button
                type="button"
                aria-label="Add Step"
                title="Add a new step"
                @click="store.addStep()"
                class="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg text-ink-gray-5 hover:text-ink-gray-9 hover:bg-surface-white/60 transition-all duration-150"
            >
                <FeatherIcon name="plus" class="size-3.5" />
                <span v-if="sectionCount <= 1">Add Step</span>
            </button>

            <!-- Divider -->
            <div class="h-4 w-px bg-outline-gray-2/60 mx-0.5" aria-hidden="true" />

            <!-- Success Page tab -->
            <button
                type="button"
                @click="store.activeSectionIndex = 'success'"
                class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150"
                :class="
                    store.activeSectionIndex === 'success'
                        ? 'bg-surface-white text-ink-green-7 shadow-xs font-semibold border border-emerald-200'
                        : 'text-ink-gray-6 hover:text-ink-green-7 hover:bg-surface-white/60'
                "
            >
                <FeatherIcon name="check-circle" class="size-3.5 text-ink-green-6" />
                <span>Success</span>
            </button>
        </div>
    </nav>
</template>
