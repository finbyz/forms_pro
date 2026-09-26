<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { Button, Badge, Dropdown, FeatherIcon, Tooltip } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import SubmissionFilterBar from "@/components/submissions/SubmissionFilterBar.vue";
import SubmissionPager from "@/components/submissions/SubmissionPager.vue";
import { useSubmissionQuery } from "@/composables/useSubmissionQuery";

const editFormStore = useEditForm();
const expandedRow = ref<string | null>(null);
const statusFilter = ref<string>("All");

const formName = computed(() => editFormStore.originalFormData?.name ?? "");

/**
 * Submissions for the builder's Submissions tab.
 *
 * Search and the status filter used to run over `submissions.value`, which held
 * only the page already fetched. Typing a name that existed on page 3 returned
 * nothing and looked like an answer. Both now go to the database, and `total`
 * counts the filtered set so the pager agrees with what is on screen.
 */
const submissionQuery = useSubmissionQuery(() => formName.value, { pageLength: 20 });
const submissions = computed(() => submissionQuery.rows.value);
const filteredSubmissions = submissions;
const total = submissionQuery.total;
const loading = submissionQuery.loading;

function fetchSubmissions() {
    return submissionQuery.fetchPage();
}

/** The status shortcut is a filter like any other, so it is applied in SQL. */
function applyStatus(status: string) {
    statusFilter.value = status;
    const others = submissionQuery.filters.value.filter(
        (entry) => !(entry.source === "column" && entry.field === "status")
    );
    submissionQuery.filters.value =
        status === "All"
            ? others
            : [...others, { source: "column", field: "status", operator: "=", value: status }];
    submissionQuery.reload();
}

watch(formName, (name) => {
    if (!name) return;
    submissionQuery.loadFilterFields();
    submissionQuery.reload();
});

function toggleExpand(name: string) {
    expandedRow.value = expandedRow.value === name ? null : name;
}

function statusTheme(status: string) {
    return status === "Success" ? "green" : status === "Failed" ? "red" : "orange";
}

function formatDate(dt: string) {
    return dt ? new Date(dt).toLocaleString() : "-";
}

function formatPayload(raw: string) {
    try {
        const parsed = JSON.parse(raw);
        return JSON.stringify(parsed, null, 2);
    } catch {
        return raw || "{}";
    }
}

/** Exports the rows on screen. The full filtered set downloads from the
 * Submissions page, which streams server-side rather than building a string
 * out of whatever the browser happens to hold. */
function exportSubmissionsCSV() {
    if (!filteredSubmissions.value.length) return;
    const headers = ["Submission ID", "Submitted At", "Status", "Target DocType", "Target Record", "Source URL", "UTM Source"];
    const rows = filteredSubmissions.value.map(s => [
        s.name,
        s.submitted_at,
        s.status,
        s.target_doctype || "",
        s.target_name || "",
        s.source_url || "",
        s.utm_source || "",
    ]);
    const csv = [headers.join(","), ...rows.map(r => r.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `submissions-${formName.value}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

const statusDropdownOptions = [
    { label: "All Status", onClick: () => applyStatus("All") },
    { label: "Success", onClick: () => applyStatus("Success") },
    { label: "Failed", onClick: () => applyStatus("Failed") },
];

onMounted(() => {
    submissionQuery.loadFilterFields();
    submissionQuery.fetchPage();
});
</script>

<template>
    <div class="flex flex-col h-full overflow-hidden bg-surface-gray-2/50">
        <!-- Header bar -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between px-6 py-4 bg-surface-base border-b border-outline-gray-1 gap-4 shrink-0 shadow-2xs">
            <div class="flex items-center gap-3">
                <div class="size-8 rounded-lg bg-surface-blue-2 text-ink-blue-7 flex items-center justify-center shrink-0">
                    <FeatherIcon name="file-text" class="size-4" />
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h2 class="text-base-semibold text-ink-gray-9 leading-tight">Form Submissions</h2>
                        <Badge variant="subtle" theme="blue" size="sm">
                            {{ total }} total
                        </Badge>
                    </div>
                    <p class="text-xs text-ink-gray-5 mt-0.5">Raw submission entries, mapped records, and responses</p>
                </div>
            </div>

            <!-- Controls -->
            <div class="flex items-center gap-2.5 flex-wrap sm:flex-nowrap">
                <!-- Status Filter Dropdown -->
                <Dropdown
                    :button="{
                        label: statusFilter === 'All' ? 'All Status' : statusFilter,
                        variant: 'outline',
                        size: 'sm',
                        iconRight: 'chevron-down',
                    }"
                    :options="statusDropdownOptions"
                />

                <Tooltip text="Refresh submissions" placement="bottom">
                    <Button variant="ghost" size="sm" icon="refresh-cw" :loading="loading" @click="fetchSubmissions" />
                </Tooltip>

                <Tooltip text="Export current submissions list as CSV" placement="bottom">
                    <Button variant="outline" size="sm" icon-left="download" @click="exportSubmissionsCSV" class="whitespace-nowrap">
                        Export CSV
                    </Button>
                </Tooltip>
            </div>
        </div>

        <div class="border-b border-outline-gray-1 bg-surface-base px-6 py-3 shrink-0">
            <SubmissionFilterBar
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
        </div>

        <!-- Table Container -->
        <div class="flex-1 overflow-auto p-6">
            <div class="bg-surface-base border border-outline-gray-1 rounded-8 shadow-2xs overflow-hidden">
                <table class="w-full text-left text-xs">
                    <thead class="bg-surface-gray-2 text-ink-gray-5 uppercase text-[11px] font-semibold border-b border-outline-gray-1 select-none">
                        <tr>
                            <th class="px-4 py-3 font-semibold">Submitted At</th>
                            <th class="px-4 py-3 font-semibold">Status</th>
                            <th class="px-4 py-3 font-semibold">Target Document</th>
                            <th class="px-4 py-3 font-semibold">Source URL</th>
                            <th class="px-4 py-3 font-semibold">UTM Source</th>
                            <th class="px-4 py-3 text-right font-semibold">Details</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-outline-gray-1/60">
                        <!-- Empty state -->
                        <template v-if="!loading && filteredSubmissions.length === 0">
                            <tr>
                                <td colspan="6" class="p-0">
                                    <div class="flex flex-col items-center justify-center py-16 text-center">
                                        <div class="size-12 rounded-full bg-surface-gray-2 flex items-center justify-center mb-3">
                                            <FeatherIcon name="inbox" class="size-6 text-ink-gray-4" />
                                        </div>
                                        <h3 class="text-sm-semibold text-ink-gray-9 mb-1">
                                            {{ submissionQuery.activeFilterCount.value || submissionQuery.search.value ? 'No matching submissions' : 'No submissions yet' }}
                                        </h3>
                                        <p class="text-xs text-ink-gray-5 max-w-sm mb-4">
                                            {{ submissionQuery.activeFilterCount.value || submissionQuery.search.value ? 'Try clearing your search or filters.' : 'Share your form with respondents or test a submission from Preview.' }}
                                        </p>
                                    </div>
                                </td>
                            </tr>
                        </template>

                        <!-- Data rows -->
                        <template v-for="s in filteredSubmissions" :key="s.name">
                            <tr
                                class="hover:bg-surface-gray-1/80 cursor-pointer transition-colors"
                                @click="toggleExpand(s.name)"
                            >
                                <td class="px-4 py-3 text-ink-gray-8 font-medium whitespace-nowrap">
                                    {{ formatDate(s.submitted_at) }}
                                </td>
                                <td class="px-4 py-3 whitespace-nowrap">
                                    <Badge :label="s.status" :theme="statusTheme(s.status)" variant="subtle" size="sm" />
                                </td>
                                <td class="px-4 py-3 text-ink-gray-7 whitespace-nowrap">
                                    <span v-if="s.target_name" class="font-mono text-2xs bg-surface-gray-2 text-ink-gray-8 px-1.5 py-0.5 rounded border border-outline-gray-1">
                                        {{ s.target_doctype }}: {{ s.target_name }}
                                    </span>
                                    <span v-else class="text-ink-gray-4 italic">No doc linked</span>
                                </td>
                                <td class="px-4 py-3 text-ink-gray-5 truncate max-w-[200px]" :title="s.source_url">
                                    {{ s.source_url || "—" }}
                                </td>
                                <td class="px-4 py-3 text-ink-gray-5 truncate max-w-[120px]">
                                    {{ s.utm_source || "—" }}
                                </td>
                                <td class="px-4 py-3 text-right">
                                    <Button
                                        variant="ghost"
                                        size="xs"
                                        :icon="expandedRow === s.name ? 'chevron-up' : 'chevron-down'"
                                        aria-label="Toggle details"
                                    />
                                </td>
                            </tr>

                            <!-- Expanded JSON row -->
                            <tr v-if="expandedRow === s.name" class="bg-surface-gray-1/60">
                                <td colspan="6" class="px-6 py-4">
                                    <div class="flex items-center justify-between mb-2">
                                        <span class="text-xs-semibold text-ink-gray-7">Response Payload & Form Values</span>
                                        <span class="text-2xs text-ink-gray-5 font-mono">ID: {{ s.name }}</span>
                                    </div>
                                    <pre class="bg-surface-base border border-outline-gray-1 rounded-6 p-3 text-2xs font-mono text-ink-gray-8 overflow-x-auto max-h-72 leading-relaxed">{{ formatPayload(s.response_json) }}</pre>
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </div>

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
        </div>
    </div>
</template>
