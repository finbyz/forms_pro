<script setup lang="ts">
import { computed } from "vue";
import { useManageForm } from "@/stores/form/manageForm";
import { useRouter } from "vue-router";

const manageFormStore = useManageForm();
const router = useRouter();

const formData = computed(() => manageFormStore.formData);
const formId = computed(() => manageFormStore.currentFormId);
const totalSubmissions = computed(() => manageFormStore.totalSubmissions);
const submissionsThisWeek = computed(() => manageFormStore.submissionsThisWeek);
const totalFields = computed(() => formData.value?.fields?.length || 0);
const targetDocType = computed(() => formData.value?.target_doctype || "");

const deskDocTypeUrl = computed(() => {
    if (!targetDocType.value) return "";
    const slug = targetDocType.value.toLowerCase().replace(/\s+/g, "-");
    return `/app/${slug}`;
});

function goToSubmissions() {
    if (formId.value) {
        router.push(`/manage/${formId.value}/submissions`);
    }
}

function goToBuilder() {
    if (formId.value) {
        router.push({ name: "Edit Form", params: { id: formId.value } });
    }
}
</script>

<template>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <!-- Card 1: Total Submissions -->
        <div
            @click="goToSubmissions"
            class="group p-4 bg-surface-base border border-outline-gray-1 rounded-8 hover:border-outline-gray-2 hover:shadow-sm cursor-pointer transition-all duration-150 flex flex-col justify-between"
        >
            <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-ink-gray-5">Total Submissions</span>
                <div class="p-2 rounded-6 bg-surface-blue-1 text-ink-blue-6 group-hover:scale-105 transition-transform">
                    <lucide-inbox class="size-4" aria-hidden="true" />
                </div>
            </div>
            <div class="mt-2.5">
                <div class="text-2xl font-bold text-ink-gray-9 tracking-tight">
                    {{ totalSubmissions }}
                </div>
                <div class="flex items-center justify-between mt-1 text-xs text-ink-gray-5">
                    <span>All-time responses</span>
                    <span class="text-ink-blue-6 group-hover:underline flex items-center gap-0.5">
                        View
                        <lucide-arrow-right class="size-3" aria-hidden="true" />
                    </span>
                </div>
            </div>
        </div>

        <!-- Card 2: Submissions This Week -->
        <div
            class="p-4 bg-surface-base border border-outline-gray-1 rounded-8 flex flex-col justify-between"
        >
            <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-ink-gray-5">Recent Activity</span>
                <div class="p-2 rounded-6 bg-emerald-50 text-emerald-600">
                    <lucide-trending-up class="size-4" aria-hidden="true" />
                </div>
            </div>
            <div class="mt-2.5">
                <div class="text-2xl font-bold text-ink-gray-9 tracking-tight">
                    {{ submissionsThisWeek }}
                </div>
                <div class="mt-1 text-xs text-ink-gray-5">
                    <span>Submissions in last 7 days</span>
                </div>
            </div>
        </div>

        <!-- Card 3: Form Fields -->
        <div
            @click="goToBuilder"
            class="group p-4 bg-surface-base border border-outline-gray-1 rounded-8 hover:border-outline-gray-2 hover:shadow-sm cursor-pointer transition-all duration-150 flex flex-col justify-between"
        >
            <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-ink-gray-5">Form Fields</span>
                <div class="p-2 rounded-6 bg-purple-50 text-purple-600 group-hover:scale-105 transition-transform">
                    <lucide-sliders class="size-4" aria-hidden="true" />
                </div>
            </div>
            <div class="mt-2.5">
                <div class="text-2xl font-bold text-ink-gray-9 tracking-tight">
                    {{ totalFields }}
                </div>
                <div class="flex items-center justify-between mt-1 text-xs text-ink-gray-5">
                    <span>Active input fields</span>
                    <span class="text-purple-600 group-hover:underline flex items-center gap-0.5">
                        Edit
                        <lucide-arrow-right class="size-3" aria-hidden="true" />
                    </span>
                </div>
            </div>
        </div>

        <!-- Card 4: Target DocType -->
        <div
            class="p-4 bg-surface-base border border-outline-gray-1 rounded-8 flex flex-col justify-between"
        >
            <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-ink-gray-5">Target DocType</span>
                <div class="p-2 rounded-6 bg-amber-50 text-amber-600">
                    <lucide-database class="size-4" aria-hidden="true" />
                </div>
            </div>
            <div class="mt-2.5">
                <div class="text-lg font-semibold text-ink-gray-9 truncate tracking-tight" :title="targetDocType">
                    {{ targetDocType || "—" }}
                </div>
                <div class="flex items-center justify-between mt-1 text-xs text-ink-gray-5">
                    <span class="truncate max-w-[120px]">{{ formData?.record_strategy || "Create New" }}</span>
                    <a
                        v-if="deskDocTypeUrl"
                        :href="deskDocTypeUrl"
                        target="_blank"
                        class="text-amber-700 hover:underline flex items-center gap-0.5 shrink-0"
                    >
                        Desk
                        <lucide-external-link class="size-2.5" aria-hidden="true" />
                    </a>
                </div>
            </div>
        </div>
    </div>
</template>
