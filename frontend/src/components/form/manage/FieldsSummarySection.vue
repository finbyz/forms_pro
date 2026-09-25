<script setup lang="ts">
import { computed } from "vue";
import { Button } from "frappe-ui";
import { useManageForm } from "@/stores/form/manageForm";
import { useRouter } from "vue-router";

const manageFormStore = useManageForm();
const router = useRouter();

const formFields = computed(() => manageFormStore.formFields);
const formId = computed(() => manageFormStore.currentFormId);

function goToBuilder() {
    if (formId.value) {
        router.push({ name: "Edit Form", params: { id: formId.value } });
    }
}
</script>

<template>
    <div class="bg-surface-base border border-outline-gray-1 rounded-8 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between">
            <div>
                <h3 class="text-base font-semibold text-ink-gray-9">Form Fields & Schema</h3>
                <p class="text-xs text-ink-gray-5 mt-0.5">
                    Overview of the {{ formFields.length }} fields configured on this form.
                </p>
            </div>
            <Button
                variant="solid"
                size="sm"
                @click="goToBuilder"
            >
                <template #prefix>
                    <lucide-edit-3 class="size-3.5 mr-1" aria-hidden="true" />
                </template>
                Edit in Builder
            </Button>
        </div>

        <div v-if="formFields.length > 0" class="overflow-x-auto">
            <table class="w-full text-left text-xs border border-outline-gray-1 rounded-6 overflow-hidden">
                <thead class="bg-surface-gray-1 border-b border-outline-gray-1 text-ink-gray-6 font-medium">
                    <tr>
                        <th class="py-2.5 px-3">#</th>
                        <th class="py-2.5 px-3">Label</th>
                        <th class="py-2.5 px-3">Fieldname</th>
                        <th class="py-2.5 px-3">Type</th>
                        <th class="py-2.5 px-3">Required</th>
                        <th class="py-2.5 px-3">Condition</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-outline-gray-1 text-ink-gray-8">
                    <tr
                        v-for="(field, idx) in formFields"
                        :key="field.fieldname || idx"
                        class="hover:bg-surface-gray-1/60 transition-colors"
                    >
                        <td class="py-2 px-3 text-ink-gray-4 font-mono">{{ idx + 1 }}</td>
                        <td class="py-2 px-3 font-medium text-ink-gray-9">
                            {{ field.label || "—" }}
                        </td>
                        <td class="py-2 px-3 font-mono text-ink-gray-5">
                            {{ field.fieldname || "—" }}
                        </td>
                        <td class="py-2 px-3">
                            <span class="px-2 py-0.5 rounded text-[11px] bg-surface-gray-2 text-ink-gray-7 border border-outline-gray-1">
                                {{ field.fieldtype }}
                            </span>
                        </td>
                        <td class="py-2 px-3">
                            <span
                                v-if="field.reqd"
                                class="inline-flex items-center text-rose-600 font-medium"
                            >
                                <lucide-asterisk class="size-3 text-rose-500 mr-0.5" aria-hidden="true" />
                                Required
                            </span>
                            <span v-else class="text-ink-gray-4">Optional</span>
                        </td>
                        <td class="py-2 px-3 text-ink-gray-5">
                            <span
                                v-if="field.conditional_logic"
                                class="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 text-[10px] font-medium"
                            >
                                Conditional
                            </span>
                            <span v-else class="text-ink-gray-4">—</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div
            v-else
            class="py-8 text-center text-xs text-ink-gray-5 border border-dashed border-outline-gray-2 rounded-6"
        >
            No fields have been added to this form yet.
            <button
                @click="goToBuilder"
                class="ml-1 text-ink-blue-6 hover:underline font-medium"
            >
                Open Studio Builder to add fields →
            </button>
        </div>
    </div>
</template>
