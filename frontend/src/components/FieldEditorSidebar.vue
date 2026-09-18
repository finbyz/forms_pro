<script setup lang="ts">
import { useEditForm } from "@/stores/editForm";
import FieldPropertiesForm from "@/components/builder/field-editor/FieldPropertiesForm.vue";

const editFormStore = useEditForm();
</script>
<template>
    <div
        class="field-editor-sidebar h-full w-[320px] border-l border-outline-gray-1 sticky top-0 overflow-y-auto flex bg-surface-base"
        data-form-builder-component="field-editor-sidebar"
    >
        <div v-if="!editFormStore.selectedField" class="w-full">
            <div
                class="flex flex-col gap-4 p-8 h-full items-center justify-center text-center"
            >
                <div class="size-14 rounded-full bg-surface-gray-2 flex items-center justify-center">
                    <svg 
                        class="size-7 text-ink-gray-5" 
                        fill="none" 
                        viewBox="0 0 24 24" 
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path 
                            stroke-linecap="round" 
                            stroke-linejoin="round" 
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
                        />
                    </svg>
                </div>
                <div class="space-y-2">
                    <h3 class="text-base-semibold text-ink-gray-8">
                        No field selected
                    </h3>
                    <p class="text-sm text-ink-gray-6 max-w-[260px]">
                        Select a field to edit its properties and configure its settings
                    </p>
                </div>
            </div>
        </div>
        <div class="w-full" v-else>
            <FieldPropertiesForm v-model="editFormStore.selectedField" />
        </div>
    </div>
</template>
