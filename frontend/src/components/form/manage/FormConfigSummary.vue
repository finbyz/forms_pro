<script setup lang="ts">
import { computed } from "vue";
import { Button } from "frappe-ui";
import { useManageForm } from "@/stores/form/manageForm";
import { useRouter } from "vue-router";

const manageFormStore = useManageForm();
const router = useRouter();

const formData = computed(() => manageFormStore.formData);
const formId = computed(() => manageFormStore.currentFormId);

const deskDocTypeUrl = computed(() => {
    const dt = formData.value?.target_doctype;
    if (!dt) return "";
    const slug = dt.toLowerCase().replace(/\s+/g, "-");
    return `/app/${slug}`;
});

function goToSettings() {
    if (formId.value) {
        router.push({ name: "Edit Form", params: { id: formId.value } });
    }
}
</script>

<template>
    <div class="bg-surface-base border border-outline-gray-1 rounded-8 p-4 flex flex-col gap-3">
        <!-- Header -->
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
                <lucide-settings class="size-4 text-ink-gray-7" aria-hidden="true" />
                <h3 class="text-sm font-semibold text-ink-gray-9">Form Configuration</h3>
            </div>
            <Button
                variant="ghost"
                size="xs"
                @click="goToSettings"
            >
                Edit in Builder
                <template #suffix>
                    <lucide-external-link class="size-3 ml-1" aria-hidden="true" />
                </template>
            </Button>
        </div>

        <!-- Settings List -->
        <div class="flex flex-col gap-2.5 text-xs">
            <!-- Target DocType -->
            <div class="flex items-center justify-between py-1.5 border-b border-outline-gray-1">
                <span class="text-ink-gray-5 flex items-center gap-1.5">
                    <lucide-database class="size-3.5" aria-hidden="true" />
                    Target DocType
                </span>
                <div class="flex items-center gap-1.5">
                    <span class="font-medium text-ink-gray-9">{{ formData?.target_doctype || "None" }}</span>
                    <a
                        v-if="deskDocTypeUrl"
                        :href="deskDocTypeUrl"
                        target="_blank"
                        class="text-ink-blue-6 hover:text-ink-blue-7"
                    >
                        <lucide-external-link class="size-3" aria-hidden="true" />
                    </a>
                </div>
            </div>

            <!-- Record Strategy -->
            <div class="flex items-center justify-between py-1.5 border-b border-outline-gray-1">
                <span class="text-ink-gray-5 flex items-center gap-1.5">
                    <lucide-workflow class="size-3.5" aria-hidden="true" />
                    Record Strategy
                </span>
                <span class="font-medium text-ink-gray-9">
                    {{ formData?.record_strategy || "Create New" }}
                </span>
            </div>

            <!-- Access Mode -->
            <div class="flex items-center justify-between py-1.5 border-b border-outline-gray-1">
                <span class="text-ink-gray-5 flex items-center gap-1.5">
                    <lucide-lock class="size-3.5" aria-hidden="true" />
                    Access Mode
                </span>
                <span
                    class="font-medium px-2 py-0.5 rounded-full text-[11px]"
                    :class="
                        formData?.login_required
                            ? 'bg-amber-50 text-amber-700'
                            : 'bg-emerald-50 text-emerald-700'
                    "
                >
                    {{ formData?.login_required ? "Login Required" : "Public Access" }}
                </span>
            </div>

            <!-- Draft / Incomplete submissions -->
            <div class="flex items-center justify-between py-1.5 border-b border-outline-gray-1">
                <span class="text-ink-gray-5 flex items-center gap-1.5">
                    <lucide-save class="size-3.5" aria-hidden="true" />
                    Allow Incomplete
                </span>
                <span class="font-medium text-ink-gray-9">
                    {{ formData?.allow_incomplete ? "Enabled (Save Drafts)" : "Disabled" }}
                </span>
            </div>

            <!-- Route Slug -->
            <div class="flex items-center justify-between py-1.5 border-b border-outline-gray-1">
                <span class="text-ink-gray-5 flex items-center gap-1.5">
                    <lucide-globe class="size-3.5" aria-hidden="true" />
                    Public Route
                </span>
                <span class="font-mono text-ink-gray-8 truncate max-w-[160px]">
                    /{{ formData?.route || "—" }}
                </span>
            </div>

            <!-- Form ID -->
            <div class="flex items-center justify-between py-1.5">
                <span class="text-ink-gray-5 flex items-center gap-1.5">
                    <lucide-file-text class="size-3.5" aria-hidden="true" />
                    Form ID
                </span>
                <span class="font-mono text-ink-gray-6 select-all">
                    {{ formData?.name || "—" }}
                </span>
            </div>
        </div>
    </div>
</template>
