<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { Button, Badge } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import { ChevronDown, ChevronUp, RefreshCw } from "@lucide/vue";

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
        const res = await (window as any).frappe.call({
            method: "forms_pro.api.v1.builder.data.get_submissions",
            args: {
                form_name: formName.value,
                limit: limit.value,
                offset: offset.value,
            },
        });
        submissions.value = res.message?.submissions ?? [];
        total.value = res.message?.total ?? 0;
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
        <div class="flex items-center justify-between px-6 py-4 bg-white border-b">
            <div>
                <h2 class="text-base font-semibold text-gray-800">Submissions</h2>
                <p class="text-sm text-gray-500 mt-0.5">{{ total }} total submission{{ total !== 1 ? "s" : "" }}</p>
            </div>
            <Button variant="ghost" :loading="loading" @click="fetchSubmissions">
                <RefreshCw class="w-4 h-4 text-gray-500" />
            </Button>
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
                            <td colspan="6" class="text-center py-16 text-gray-400">
                                No submissions yet. Share your form to start collecting responses.
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
                                <ChevronDown v-if="expandedRow !== s.name" class="w-4 h-4 text-gray-400 ml-auto" />
                                <ChevronUp v-else class="w-4 h-4 text-gray-400 ml-auto" />
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
