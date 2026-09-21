<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { Button, Badge, FormControl, createResource } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";

const editFormStore = useEditForm();
const submissions = ref<any[]>([]);
const total = ref(0);
const limit = ref(50);
const offset = ref(0);
const loading = ref(false);
const expandedRow = ref<string | null>(null);

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

function toggleExpand(name: string) {
    expandedRow.value = expandedRow.value === name ? null : name;
}

function statusTheme(status: string) {
    return status === "Success" ? "green" : status === "Failed" ? "red" : "orange";
}

function formatDate(dt: string) {
    return dt ? new Date(dt).toLocaleString() : "-";
}

function loadMore() {
    offset.value += limit.value;
    fetchSubmissions();
}

onMounted(() => {
    fetchSubmissions();
});
</script>

<template>
    <div class="flex flex-col h-full overflow-hidden bg-gray-50">
        <!-- Header bar -->
        <div class="flex flex-col px-6 py-6 bg-surface-base border-b border-outline-gray-1 gap-4">
            <div class="flex items-center justify-between">
                <div>
                    <h2 class="text-xl font-bold text-ink-gray-9">Submissions</h2>
                    <p class="text-sm text-ink-gray-5 mt-1">{{ total }} total submission{{ total !== 1 ? "s" : "" }}</p>
                </div>
                <div class="flex items-center gap-2">
                    <FormControl
                        type="search"
                        placeholder="Search submissions..."
                        variant="outline"
                        size="sm"
                        class="w-56"
                    />
                    <div class="border rounded-md border-outline-gray-2 px-3 py-1.5 text-sm text-ink-gray-7 bg-surface-base cursor-not-allowed opacity-70 flex items-center gap-2">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                        Select date range
                    </div>
                    <div class="border rounded-md border-outline-gray-2 px-3 py-1.5 text-sm text-ink-gray-7 bg-surface-base cursor-not-allowed opacity-70 flex items-center gap-2 w-32 justify-between">
                        <span class="flex items-center gap-2">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
                            All Status
                        </span>
                        <span class="lucide-chevron-down w-4 h-4 text-ink-gray-4" aria-hidden="true" />
                    </div>
                    <Button variant="outline" :loading="loading" @click="fetchSubmissions">
                        <span class="lucide-refresh-cw w-4 h-4 text-ink-gray-7" aria-hidden="true" />
                    </Button>
                    <Button variant="outline" icon-left="download" class="text-ink-gray-7">Export CSV</Button>
                </div>
            </div>
        </div>

        <!-- Table -->
        <div class="flex-1 overflow-auto">
            <table class="w-full text-sm">
                <thead class="sticky top-0 bg-gray-100 text-gray-600 uppercase text-xs">
                    <tr>
                        <th class="px-4 py-3 text-left font-medium">Submitted At</th>
                        <th class="px-4 py-3 text-left font-medium">Status</th>
                        <th class="px-4 py-3 text-left font-medium">Target</th>
                        <th class="px-4 py-3 text-left font-medium">Source</th>
                        <th class="px-4 py-3 text-left font-medium">UTM</th>
                        <th class="px-4 py-3 text-right font-medium">Detail</th>
                    </tr>
                </thead>
                <tbody>
                    <template v-if="!loading && submissions.length === 0">
                        <tr>
                            <td colspan="6" class="p-0">
                                <div class="flex flex-col items-center justify-center py-24 bg-white border rounded-lg m-4 mt-8 shadow-sm">
                                    <div class="w-16 h-16 rounded-full bg-surface-gray-2 flex items-center justify-center mb-6">
                                        <span class="lucide-file-text w-8 h-8 text-ink-gray-4" aria-hidden="true" />
                                    </div>
                                    <h3 class="text-lg font-semibold text-ink-gray-9 mb-1">No submissions yet</h3>
                                    <p class="text-sm text-ink-gray-5 mb-6">Share your form to start collecting responses.</p>
                                    <div class="flex items-center gap-3">
                                        <Button variant="outline" size="md">
                                            <template #prefix><span class="lucide-link-2 w-4 h-4 mr-1.5" aria-hidden="true" /></template>
                                            Copy Form Link
                                        </Button>
                                        <Button variant="solid" theme="blue" size="md">
                                            <template #prefix><span class="lucide-external-link w-4 h-4 mr-1.5" aria-hidden="true" /></template>
                                            Open Form
                                        </Button>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    </template>
                    <template v-for="s in submissions" :key="s.name">
                        <tr
                            class="border-b hover:bg-white cursor-pointer transition-colors"
                            @click="toggleExpand(s.name)"
                        >
                            <td class="px-4 py-3 text-gray-700">{{ formatDate(s.submitted_at) }}</td>
                            <td class="px-4 py-3">
                                <Badge :label="s.status" :theme="statusTheme(s.status)" variant="subtle" size="sm" />
                            </td>
                            <td class="px-4 py-3 text-gray-600">
                                <span v-if="s.target_name" class="font-mono text-xs bg-gray-100 px-1 rounded">{{ s.target_doctype }}/{{ s.target_name }}</span>
                                <span v-else class="text-gray-400">-</span>
                            </td>
                            <td class="px-4 py-3 text-gray-500 text-xs truncate max-w-[180px]">{{ s.source_url || "-" }}</td>
                            <td class="px-4 py-3 text-gray-500 text-xs">{{ s.utm_source || "-" }}</td>
                            <td class="px-4 py-3 text-right">
                                <span class="lucide-chevron-down w-4 h-4 text-gray-400" v-if="expandedRow !== s.name" aria-hidden="true" />
                                <span class="lucide-chevron-up w-4 h-4 text-gray-400" v-else aria-hidden="true" />
                            </td>
                        </tr>
                        <tr v-if="expandedRow === s.name" class="bg-white border-b">
                            <td colspan="6" class="px-6 py-4">
                                <div class="text-xs font-semibold text-gray-500 mb-2">Response Payload</div>
                                <pre class="bg-gray-50 border rounded p-3 text-xs text-gray-700 overflow-x-auto">{{ s.response_json || "{}" }}</pre>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>

        <!-- Load more -->
        <div v-if="submissions.length < total" class="flex justify-center py-4 border-t bg-white">
            <Button variant="subtle" :loading="loading" @click="loadMore">Load More</Button>
        </div>
    </div>
</template>
