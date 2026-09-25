<script setup lang="ts">
import { useManageForm } from "@/stores/form/manageForm";

import { ListView, Badge, createResource, Dropdown, Button, Tooltip } from "frappe-ui";
import { formatDateTime } from "@/utils/date";
import Avatar from "@/components/ui/Avatar.vue";
import Drawer from "@/components/ui/Drawer.vue";
import SubmissionDetails from "@/components/form/submissions/SubmissionDetails.vue";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";

const route = useRoute();
const router = useRouter();
const drawerOpen = ref(false);
const selectedSubmission = ref<Record<string, any> | null>(null);
const loadedSubmissionDetails = ref<Record<string, any> | null>(null);
const isRefreshing = ref(false);

const manageFormStore = useManageForm();
const effectiveFormId = computed(() => (route.params.formId as string) || manageFormStore.currentFormId);

function onRowClick(row: Record<string, any>) {
    selectedSubmission.value = row;
    loadedSubmissionDetails.value = null;
    drawerOpen.value = true;
    syncQuery(row.name);
}

/**
 * Keep the open submission in the URL.
 *
 * Opening a submission used to change nothing in the address bar, so the view
 * could not be linked to, refreshed or shared -- and the desk had no address to
 * send someone to. `replace` rather than `push`, so browsing submissions does
 * not fill the back button with drawer states.
 */
function syncQuery(submission?: string | null) {
    const current = (route.query.submission as string | undefined) ?? undefined;
    if (current === (submission ?? undefined)) return;

    const query: Record<string, any> = { ...route.query };
    if (submission) query.submission = submission;
    else delete query.submission;
    router.replace({ query }).catch(() => {
        /* navigating away mid-update is not an error worth surfacing */
    });
}

// Closing the drawer (backdrop, Esc, the X) must clear the deep link too.
watch(drawerOpen, (open) => {
    if (!open) syncQuery(null);
});

function onSubmissionLoaded(data: Record<string, any>) {
    loadedSubmissionDetails.value = data;
}

const deskUrl = computed(() => {
    const targetDocType = loadedSubmissionDetails.value?.target_doctype || manageFormStore.formData?.target_doctype;
    const targetName = loadedSubmissionDetails.value?.target_name;
    if (targetDocType && targetName) {
        const slug = targetDocType.toLowerCase().replace(/\s+/g, "-");
        return `/app/${slug}/${encodeURIComponent(targetName)}`;
    }
    if (targetDocType && selectedSubmission.value?.name) {
        const slug = targetDocType.toLowerCase().replace(/\s+/g, "-");
        return `/app/${slug}/${encodeURIComponent(selectedSubmission.value.name)}`;
    }
    if (selectedSubmission.value?.name) {
        return `/app/fp-form-submission/${encodeURIComponent(selectedSubmission.value.name)}`;
    }
    return "";
});

function openDeskForm() {
    if (deskUrl.value) {
        window.open(deskUrl.value, "_blank");
    }
}

const allSubmissionsResource = createResource({
    url: "forms_pro.api.submission.get_all_submissions",
    makeParams() {
        return {
            form_id: effectiveFormId.value,
        };
    },
    onError(error: Error) {
        toast.error("Failed to fetch submissions", {
            description: error.message,
        });
    },
});
const allSubmissions = computed(() => allSubmissionsResource.data ?? []);

/**
 * Deep link from the desk: a record created by a form carries a button that
 * opens .../submissions?submission=<id>, so whoever was looking at a Contact
 * lands straight on that submission's answers rather than hunting the list.
 *
 * Driven by a watcher rather than `onMounted`, because the rows arrive
 * asynchronously and may also be replaced by a reload.
 */
let openedFromQuery = false;

watch(
    [allSubmissions, () => route.query.submission],
    ([rows, wanted]) => {
        if (!wanted || openedFromQuery || !rows?.length) return;
        const match = (rows as Record<string, any>[]).find((row) => row.name === wanted);
        if (!match) return;
        openedFromQuery = true;
        selectedSubmission.value = match;
        loadedSubmissionDetails.value = null;
        drawerOpen.value = true;
    },
    { immediate: true }
);

allSubmissionsResource.fetch();

async function refreshSubmissions() {
    isRefreshing.value = true;
    try {
        await allSubmissionsResource.fetch({ form_id: effectiveFormId.value });
        toast.success("Submissions reloaded");
    } catch (error: any) {
        toast.error("Failed to reload submissions", {
            description: error?.message,
        });
    } finally {
        isRefreshing.value = false;
    }
}

defineExpose({
    refreshSubmissions,
    isRefreshing,
});

const columns = computed(() => [
    {
        label: "ID",
        key: "name",
        width: 1,
    },
    {
        label: "Status",
        key: "submission_status",
        width: 1,
    },
    {
        label: "Submitted On",
        key: "creation",
        width: 2,
    },
    {
        label: "Last Modified",
        key: "modified",
        width: 2,
    },
    {
        label: "Submitted By",
        key: "owner",
        width: 1,
    },
]);

const onExport = (fileType: "CSV" | "Excel") => {
    const formId = effectiveFormId.value;
    if (!formId) {
        toast.error("Unable to export", { description: "No form selected." });
        return;
    }
    const params = new URLSearchParams({ form_id: formId, file_type: fileType });
    window.location.href = `/api/method/forms_pro.api.export.export_submissions?${params}`;
};

const dropdownItems = computed(() => [
    {
        label: "Export as CSV",
        icon: "file-text",
        onClick: () => onExport("CSV"),
    },
    {
        label: "Export as Excel",
        icon: "file",
        onClick: () => onExport("Excel"),
    },
]);
</script>
<template>
    <div>
        <Dropdown
            :button="{
                label: 'Export',
                iconLeft: 'download',
            }"
            :options="dropdownItems"
        />
    </div>
    <ListView
        :columns="columns"
        :rows="allSubmissions"
        :options="{
            selectable: false,
            showTooltip: false,
            onRowClick,
            emptyState: {
                title: 'No Submissions Yet',
                description: 'Submissions for this form will appear here.',
            },
        }"
        row-key="name"
    >
        <!-- @vue-expect-error -->
        <template #cell="{ item, row, column }">
            <div v-if="column.key === 'owner'" class="flex items-center gap-2">
                <Avatar v-if="row.owner !== 'Guest'" :userId="row.owner" />
                <span class="text-sm text-ink-gray-8">{{ row.owner }}</span>
            </div>
            <span v-else-if="column.key === 'name'" class="text-xs text-ink-gray-6 font-mono">
                {{ row.name }}
            </span>
            <Badge
                v-else-if="column.key === 'submission_status'"
                :label="row.submission_status"
                :variant="row.submission_status === 'Submitted' ? 'subtle' : 'outline'"
            />
            <span v-else-if="column.key === 'creation'" class="text-sm text-ink-gray-6">
                {{ formatDateTime(row.creation) }}
            </span>
            <span v-else-if="column.key === 'modified'" class="text-sm text-ink-gray-6">
                {{ formatDateTime(row.modified) }}
            </span>
            <span v-else class="text-sm">{{ item }}</span>
        </template>
    </ListView>

    <Drawer v-model="drawerOpen" size="lg" title="Submission Details">
        <template #header-actions>
            <Tooltip v-if="selectedSubmission && deskUrl" text="Open in Desk Form View" placement="bottom">
                <Button
                    variant="subtle"
                    size="sm"
                    icon="external-link"
                    @click="openDeskForm"
                >
                    View in Desk
                </Button>
            </Tooltip>
        </template>
        <SubmissionDetails
            v-if="selectedSubmission"
            :submissionId="selectedSubmission.name"
            :doctype="manageFormStore.formData?.target_doctype ?? ''"
            @loaded="onSubmissionLoaded"
        />
        <div v-else-if="selectedSubmission" class="text-sm text-ink-gray-5">Loading...</div>
    </Drawer>
</template>
