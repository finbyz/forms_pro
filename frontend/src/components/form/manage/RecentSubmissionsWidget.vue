<script setup lang="ts">
import { computed } from "vue";
import { Button, Tooltip } from "frappe-ui";
import { useManageForm } from "@/stores/form/manageForm";
import Avatar from "@/components/ui/Avatar.vue";
import { formatPrettyDate, formatDateTime } from "@/utils/date";
import { useRouter } from "vue-router";
import { useClipboard } from "@vueuse/core";
import { toast } from "vue-sonner";

const manageFormStore = useManageForm();
const router = useRouter();
const { copy } = useClipboard();

const recentSubmissions = computed(() => manageFormStore.recentSubmissions);
const totalSubmissions = computed(() => manageFormStore.totalSubmissions);
const formId = computed(() => manageFormStore.currentFormId);
const formData = computed(() => manageFormStore.formData);

function goToSubmissions() {
    if (formId.value) {
        router.push(`/manage/${formId.value}/submissions`);
    }
}

function copyLink() {
    const route = formData.value?.route;
    if (route) {
        const url = `${window.location.origin}/forms/p/${route}`;
        copy(url);
        toast.success("Form link copied to clipboard");
    }
}

function getStatusBadgeClass(status: string) {
    const s = (status || "").toLowerCase();
    if (s === "success" || s === "submitted") {
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
    }
    if (s === "draft") {
        return "bg-amber-50 text-amber-700 border-amber-200";
    }
    if (s === "failed") {
        return "bg-rose-50 text-rose-700 border-rose-200";
    }
    return "bg-surface-gray-2 text-ink-gray-7 border-outline-gray-2";
}

function openTargetRecord(doctype?: string, name?: string) {
    if (doctype && name) {
        const slug = doctype.toLowerCase().replace(/\s+/g, "-");
        window.open(`/app/${slug}/${encodeURIComponent(name)}`, "_blank");
    }
}
</script>

<template>
    <div class="bg-surface-base border border-outline-gray-1 rounded-8 p-4 flex flex-col gap-3">
        <!-- Header -->
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
                <lucide-list-checks class="size-4 text-ink-gray-7" aria-hidden="true" />
                <h3 class="text-sm font-semibold text-ink-gray-9">Recent Submissions</h3>
                <span
                    v-if="totalSubmissions > 0"
                    class="text-xs font-medium px-2 py-0.5 rounded-full bg-surface-gray-2 text-ink-gray-6"
                >
                    {{ totalSubmissions }}
                </span>
            </div>

            <Button
                v-if="totalSubmissions > 0"
                variant="ghost"
                size="sm"
                @click="goToSubmissions"
            >
                View all
                <template #suffix>
                    <lucide-arrow-right class="size-3.5 ml-1" aria-hidden="true" />
                </template>
            </Button>
        </div>

        <!-- Content: Table or Empty State -->
        <div v-if="recentSubmissions.length > 0" class="flex flex-col divide-y divide-outline-gray-1">
            <div
                v-for="sub in recentSubmissions"
                :key="sub.name"
                class="py-2.5 flex items-center justify-between gap-3 text-xs hover:bg-surface-gray-1 px-2 rounded-6 transition-colors"
            >
                <!-- Left: ID & Submitter -->
                <div class="flex items-center gap-2.5 min-w-0">
                    <Avatar :userId="sub.owner" size="sm" />
                    <div class="flex flex-col min-w-0">
                        <span class="font-medium text-ink-gray-9 truncate">
                            {{ sub.owner || "Guest" }}
                        </span>
                        <span class="text-[11px] font-mono text-ink-gray-5 truncate">
                            {{ sub.name }}
                        </span>
                    </div>
                </div>

                <!-- Middle: Status Pill -->
                <div class="flex items-center gap-2 shrink-0">
                    <span
                        class="text-[11px] font-medium px-2 py-0.5 rounded-full border"
                        :class="getStatusBadgeClass(sub.status)"
                    >
                        {{ sub.status || "Submitted" }}
                    </span>
                </div>

                <!-- Right: Date & Desk Link -->
                <div class="flex items-center gap-2 shrink-0 text-ink-gray-5">
                    <Tooltip :text="formatDateTime(sub.creation)" placement="bottom">
                        <span class="whitespace-nowrap">
                            {{ formatPrettyDate(sub.creation) }}
                        </span>
                    </Tooltip>

                    <Tooltip
                        v-if="sub.target_doctype && sub.target_name"
                        :text="`Open ${sub.target_doctype}: ${sub.target_name}`"
                        placement="bottom"
                    >
                        <Button
                            variant="ghost"
                            size="xs"
                            @click="openTargetRecord(sub.target_doctype, sub.target_name)"
                        >
                            <lucide-external-link class="size-3.5 text-ink-gray-6" aria-hidden="true" />
                        </Button>
                    </Tooltip>
                </div>
            </div>
        </div>

        <!-- Empty State -->
        <div
            v-else
            class="flex flex-col items-center justify-center py-8 px-4 text-center bg-surface-gray-1 rounded-6 border border-dashed border-outline-gray-2"
        >
            <div class="p-3 rounded-full bg-surface-base text-ink-gray-4 shadow-sm mb-3">
                <lucide-inbox class="size-6 text-ink-gray-5" aria-hidden="true" />
            </div>
            <h4 class="text-sm font-semibold text-ink-gray-8">No submissions yet</h4>
            <p class="text-xs text-ink-gray-5 max-w-sm mt-1 mb-4">
                Responses will show up here as soon as respondents complete your form.
            </p>
            <Button
                variant="outline"
                size="sm"
                @click="copyLink"
            >
                <template #prefix>
                    <lucide-copy class="size-3.5 mr-1" aria-hidden="true" />
                </template>
                Copy Public Link to Share
            </Button>
        </div>

        <!-- Footer link when submissions exist -->
        <div v-if="totalSubmissions > 5" class="pt-1 text-center">
            <button
                @click="goToSubmissions"
                class="text-xs text-ink-blue-6 hover:text-ink-blue-7 hover:underline font-medium inline-flex items-center gap-1"
            >
                View remaining {{ totalSubmissions - 5 }} submissions in the Submissions tab
                <lucide-arrow-right class="size-3" aria-hidden="true" />
            </button>
        </div>
    </div>
</template>
