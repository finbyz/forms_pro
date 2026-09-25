<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { Button, Badge, FormControl, Dropdown, FeatherIcon, Tooltip, createResource } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";

const editFormStore = useEditForm();
const submissions = ref<any[]>([]);
const total = ref(0);
const limit = ref(50);
const offset = ref(0);
const loading = ref(false);
const expandedRow = ref<string | null>(null);
const searchQuery = ref("");
const statusFilter = ref<string>("All");

const formName = computed(() => editFormStore.originalFormData?.name ?? "");

async function fetchSubmissions() {
    if (!formName.value) return;
    loading.value = true;
    try {
        const res = await createResource({
            url: "forms_pro.api.v1.builder.data.get_submissions",
            makeParams() {
                return {
                    form_name: formName.value,
                    limit: limit.value,
                    offset: offset.value,
                };
            }
        }).submit();
        submissions.value = res?.submissions ?? [];
        total.value = res?.total ?? 0;
    } catch (err) {
        console.error("Failed to load submissions", err);
    } finally {
        loading.value = false;
    }
}

const filteredSubmissions = computed(() => {
    let list = submissions.value;
    if (statusFilter.value !== "All") {
        list = list.filter(s => s.status === statusFilter.value);
    }
    if (searchQuery.value.trim()) {
        const q = searchQuery.value.toLowerCase().trim();
        list = list.filter(s =>
            (s.name && s.name.toLowerCase().includes(q)) ||
            (s.target_name && s.target_name.toLowerCase().includes(q)) ||
            (s.target_doctype && s.target_doctype.toLowerCase().includes(q)) ||
            (s.source_url && s.source_url.toLowerCase().includes(q)) ||
            (s.utm_source && s.utm_source.toLowerCase().includes(q)) ||
            (s.response_json && s.response_json.toLowerCase().includes(q))
        );
    }
    return list;
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

function loadMore() {
    offset.value += limit.value;
    fetchSubmissions();
}

const statusDropdownOptions = [
    { label: "All Status", onClick: () => { statusFilter.value = "All"; } },
    { label: "Success", onClick: () => { statusFilter.value = "Success"; } },
    { label: "Failed", onClick: () => { statusFilter.value = "Failed"; } },
];

onMounted(() => {
    fetchSubmissions();
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
                <FormControl
                    type="search"
                    placeholder="Search submissions..."
                    v-model="searchQuery"
                    variant="outline"
                    size="sm"
                    class="w-48 sm:w-60"
                />

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
                                            {{ searchQuery || statusFilter !== 'All' ? 'No matching submissions' : 'No submissions yet' }}
                                        </h3>
                                        <p class="text-xs text-ink-gray-5 max-w-sm mb-4">
                                            {{ searchQuery || statusFilter !== 'All' ? 'Try clearing your search or status filters.' : 'Share your form with respondents or test a submission from Preview.' }}
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

            <!-- Load more -->
            <div v-if="submissions.length < total" class="flex justify-center py-4 mt-2">
                <Button variant="subtle" size="sm" :loading="loading" @click="loadMore">
                    Load More ({{ submissions.length }} of {{ total }})
                </Button>
            </div>
        </div>
    </div>
</template>
