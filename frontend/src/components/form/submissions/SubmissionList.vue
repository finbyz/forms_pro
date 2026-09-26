<script setup lang="ts">
import { useManageForm } from "@/stores/form/manageForm";

import { ListView, Badge, Dropdown, Button, Tooltip } from "frappe-ui";
import SubmissionFilterBar from "@/components/submissions/SubmissionFilterBar.vue";
import SubmissionPager from "@/components/submissions/SubmissionPager.vue";
import { useSubmissionQuery } from "@/composables/useSubmissionQuery";
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

/**
 * Submissions arrive one page at a time.
 *
 * This list used to call `get_all_submissions`, which had no limit: a form
 * that had collected for a year handed every row to the browser at once, and
 * there was no way to narrow them. Paging, sorting and filtering now happen in
 * the database.
 */
const submissionQuery = useSubmissionQuery(() => effectiveFormId.value, { pageLength: 20 });
const allSubmissions = computed(() => submissionQuery.rows.value);

watch(
    () => submissionQuery.error.value,
    (message) => {
        if (message) toast.error("Failed to fetch submissions", { description: message });
    }
);

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
        if (!wanted || openedFromQuery) return;
        const match = (rows as Record<string, any>[] | undefined)?.find((row) => row.name === wanted);
        openedFromQuery = true;
        // A deep-linked submission need not be on the page being shown, so open
        // it by id rather than requiring it in the loaded rows.
        selectedSubmission.value = match ?? { name: wanted };
        loadedSubmissionDetails.value = null;
        drawerOpen.value = true;
    },
    { immediate: true }
);

submissionQuery.loadFilterFields();
submissionQuery.fetchPage();

// Switching forms must reset the pager as well as the rows, or page 4 of the
// previous form silently becomes page 4 of this one.
watch(effectiveFormId, (formId) => {
    if (!formId) return;
    submissionQuery.loadFilterFields();
    submissionQuery.reload();
});

async function refreshSubmissions() {
    isRefreshing.value = true;
    try {
        await submissionQuery.fetchPage();
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
    // Export what the operator is looking at, not the whole form.
    const params = new URLSearchParams({ form_id: formId, file_type: fileType });
    if (submissionQuery.search.value.trim()) params.set("search", submissionQuery.search.value.trim());
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
    <div class="flex flex-wrap items-start justify-between gap-3">
        <SubmissionFilterBar
            class="flex-1 min-w-0"
            :filters="submissionQuery.filters.value"
            :columnFields="submissionQuery.columnFields.value"
            :answerFields="submissionQuery.answerFields.value"
            :operators="submissionQuery.operators.value"
            :search="submissionQuery.search.value"
            :activeFilterCount="submissionQuery.activeFilterCount.value"
            :loading="submissionQuery.loading.value"
            @update:search="(value: string) => (submissionQuery.search.value = value)"
            @add="submissionQuery.addFilter"
            @remove="submissionQuery.removeFilter"
            @apply="submissionQuery.reload"
            @clear="submissionQuery.clearFilters"
        />
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

    <SubmissionPager
        :rangeFrom="submissionQuery.rangeFrom.value"
        :rangeTo="submissionQuery.rangeTo.value"
        :total="submissionQuery.total.value"
        :page="submissionQuery.page.value"
        :pageCount="submissionQuery.pageCount.value"
        :pageLength="submissionQuery.pageLength.value"
        :pageLengths="submissionQuery.pageLengths.value"
        :hasMore="submissionQuery.hasMore.value"
        :loading="submissionQuery.loading.value"
        @previous="submissionQuery.previousPage"
        @next="submissionQuery.nextPage"
        @update:pageLength="(value: number) => (submissionQuery.pageLength.value = value)"
    />

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
