<script setup lang="ts">
import { useManageForm } from "@/stores/form/manageForm";
import { Breadcrumbs, Button, Tooltip } from "frappe-ui";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import SubmissionList from "@/components/form/submissions/SubmissionList.vue";

const route = useRoute();
const manageFormStore = useManageForm();
const submissionListRef = ref<any>(null);

const formId = computed(
    () => (route.params.formId as string) || manageFormStore.currentFormId
);

const breadcrumbItems = computed(() => [
    { label: "Manage Form", to: `/manage/${formId.value}/overview` },
    { label: "Submissions" },
]);

const isReloading = computed(() => submissionListRef.value?.isRefreshing ?? false);

function handleReload() {
    submissionListRef.value?.refreshSubmissions?.();
}
</script>

<template>
    <div class="flex flex-col gap-4 w-full">
        <Breadcrumbs :items="breadcrumbItems" />
        <div class="flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <div class="flex gap-3 items-center text-ink-gray-8">
                    <lucide-list-checks class="w-6 h-6" aria-hidden="true" />
                    <h2 class="text-2xl font-bold">Submissions</h2>
                </div>
                <Tooltip text="Reload submissions list" placement="left">
                    <Button
                        variant="outline"
                        size="sm"
                        icon-left="refresh-cw"
                        :loading="isReloading"
                        @click="handleReload"
                    >
                        Reload
                    </Button>
                </Tooltip>
            </div>
            <p class="text-ink-gray-5 text-sm">
                Form submissions for
                <span class="text-sm p-1 bg-surface-gray-1 font-mono rounded">{{
                    manageFormStore.formData?.title || formId
                }}</span>
                will appear here.
            </p>
            <SubmissionList ref="submissionListRef" />
        </div>
    </div>
</template>
