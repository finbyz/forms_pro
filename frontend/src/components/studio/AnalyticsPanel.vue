<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { Button, FormControl, createResource } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";

const editFormStore = useEditForm();
const summary = ref<any>({ total: 0, success: 0, failed: 0, created: 0, updated: 0, conversion_rate: 0 });
const sources = ref<any>({ utm_sources: [], referrers: [] });
const timeseries = ref<any>({ dates: [], counts: [] });
const loading = ref(false);

const formName = computed(() => editFormStore.originalFormData?.name ?? "");

const dateRange = ref<{ start: string; end: string }>({
  start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
  end: new Date().toISOString().split("T")[0],
});

const presets = [
  { label: "Today", days: 0 },
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
  { label: "All time", days: -1 },
];

function applyPreset(days: number) {
  const end = new Date();
  const start = days === -1 ? new Date("2020-01-01") : new Date(Date.now() - days * 24 * 60 * 60 * 1000);
  dateRange.value = {
    start: start.toISOString().split("T")[0],
    end: end.toISOString().split("T")[0],
  };
  fetchAnalytics();
}

async function fetchAnalytics() {
  if (!formName.value) return;
  loading.value = true;
  try {
    const [sum, src, ts] = await Promise.all([
      createResource({
        url: "forms_pro.api.v1.builder.analytics.summary",
        makeParams() {
          return { form_name: formName.value, start_date: dateRange.value.start, end_date: dateRange.value.end };
        },
      }).submit(),
      createResource({
        url: "forms_pro.api.v1.builder.analytics.sources",
        makeParams() {
          return { form_name: formName.value };
        },
      }).submit(),
      createResource({
        url: "forms_pro.api.v1.builder.analytics.timeseries",
        makeParams() {
          return { form_name: formName.value, start_date: dateRange.value.start, end_date: dateRange.value.end };
        },
      }).submit(),
    ]);
    summary.value = sum ?? { total: 0, success: 0, failed: 0, created: 0, updated: 0, conversion_rate: 0 };
    sources.value = src ?? { utm_sources: [], referrers: [] };
    timeseries.value = ts ?? { dates: [], counts: [] };
  } finally {
    loading.value = false;
  }
}

function exportCSV() {
  const rows = timeseries.value.dates.map((date: string, i: number) => ({
    date,
    submissions: timeseries.value.counts[i],
  }));
  const csv = ["Date,Submissions", ...rows.map(r => `${r.date},${r.submissions}`)].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `analytics-${formName.value}-${dateRange.value.start}-to-${dateRange.value.end}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

watch(() => editFormStore.formData, () => {
  if (formName.value) fetchAnalytics();
}, { immediate: true });

const kpis = computed(() => {
  const sum = summary.value;
  
  let convRateDisplay = "—";
  if (typeof sum.conversion_rate === "number") {
    convRateDisplay = sum.conversion_rate + "%";
  } else if (sum.conversion_rate === "0" || sum.conversion_rate === 0) {
    convRateDisplay = "0%";
  }

  return [
    { label: "Total", value: sum.total, icon: "lucide-bar-chart-3", color: "text-ink-blue-6" },
    { label: "Success", value: sum.success, icon: "lucide-trending-up", color: "text-ink-green-6" },
    { label: "Failed", value: sum.failed, icon: "lucide-bar-chart-3", color: "text-ink-red-6" },
    { label: "Created", value: sum.created, icon: "lucide-users", color: "text-ink-purple-6" },
    { label: "Updated", value: sum.updated, icon: "lucide-users", color: "text-ink-indigo-6" },
    { label: "Conv. Rate", value: convRateDisplay, icon: "lucide-trending-up", color: "text-ink-orange-6" },
  ];
});

const maxCount = computed(() => Math.max(...timeseries.value.counts, 0) || 1);
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface-gray-1">
    <div class="flex flex-col items-start justify-between px-6 py-5 bg-surface-base border-b border-outline-gray-1 gap-5">
      <div>
        <h2 class="text-lg-semibold text-ink-gray-9">Analytics</h2>
        <p class="text-sm text-ink-gray-5 mt-1">Track submissions and conversions</p>
      </div>
      <div class="flex items-center gap-3 flex-wrap w-full">
        <div class="flex items-center gap-2">
          <span class="lucide-calendar text-ink-gray-5" aria-hidden="true" />
          <FormControl type="date" size="sm" v-model="dateRange.start" @change="fetchAnalytics" />
          <span class="text-ink-gray-5 text-sm">to</span>
          <FormControl type="date" size="sm" v-model="dateRange.end" @change="fetchAnalytics" />
        </div>
        <div class="flex gap-2">
          <Button 
            v-for="p in presets" 
            :key="p.label" 
            variant="outline"
            size="sm"
            @click="applyPreset(p.days)"
          >
            {{ p.label }}
          </Button>
        </div>
        <div class="flex items-center gap-2 ml-auto">
          <Button variant="ghost" :loading="loading" @click="fetchAnalytics"><span class="lucide-calendar mr-1.5" aria-hidden="true" /> Refresh</Button>
          <Button variant="outline" size="sm" @click="exportCSV"><span class="lucide-download mr-1.5" aria-hidden="true" /> Export CSV</Button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-6">
      <!-- KPI Cards -->
      <div class="grid grid-cols-3 gap-5 mb-8">
        <div v-for="kpi in kpis" :key="kpi.label" class="bg-surface-base rounded-6 border border-outline-gray-1 p-5 flex items-center gap-4 hover:border-outline-gray-2 transition-all duration-200 ease-out">
          <span :class="[kpi.icon, kpi.color, 'size-9 shrink-0']" aria-hidden="true" />
          <div>
            <p class="text-xs text-ink-gray-5">{{ kpi.label }}</p>
            <p class="text-2xl-semibold text-ink-gray-9">{{ kpi.value }}</p>
          </div>
        </div>
      </div>

      <!-- Timeseries Chart -->
      <div class="bg-surface-base rounded-6 border border-outline-gray-1 p-6 mb-8">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-sm-semibold text-ink-gray-7">
            <span class="lucide-trending-up inline mr-1.5" aria-hidden="true" /> Daily Submissions
          </h3>
          <span class="text-xs text-ink-gray-5">{{ dateRange.start }} to {{ dateRange.end }}</span>
        </div>
        <div class="h-72 relative">
          <div v-if="!timeseries.dates?.length" class="flex items-center justify-center h-full text-ink-gray-5">
            No data for selected range
          </div>
          <div v-else class="h-full flex items-end justify-center gap-2.5 px-2">
            <div v-for="(count, i) in timeseries.counts" :key="i" class="flex-1 flex flex-col items-center min-w-[10px]">
              <div
                class="w-full bg-surface-blue-6 rounded-t transition-all duration-200 ease-out hover:bg-surface-blue-7 cursor-pointer active:scale-95"
                :style="{ height: (count / maxCount) * 100 + '%', minHeight: count > 0 ? '4px' : '0' }"
                :title="timeseries.dates[i] + ': ' + count"
              ></div>
              <span class="text-[10px] text-ink-gray-5 mt-1.5 whitespace-nowrap">{{ timeseries.dates[i].slice(5) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Sources -->
      <div class="grid grid-cols-2 gap-6">
        <div class="bg-surface-base rounded-6 border border-outline-gray-1 p-6">
          <h3 class="text-sm-semibold text-ink-gray-7 mb-4">
            <span class="lucide-globe inline mr-1.5" aria-hidden="true" /> UTM Sources
          </h3>
          <div v-if="!sources.utm_sources?.length" class="text-sm text-ink-gray-5 py-5 text-center">
            No UTM data yet
          </div>
          <div v-else class="flex flex-col gap-3">
            <div v-for="s in sources.utm_sources" :key="s.source" class="flex justify-between text-sm">
              <span class="text-ink-gray-7">{{ s.source || "(direct)" }}</span>
              <span class="font-medium text-ink-gray-9">{{ s.count }}</span>
            </div>
          </div>
        </div>

        <div class="bg-surface-base rounded-6 border border-outline-gray-1 p-6">
          <h3 class="text-sm-semibold text-ink-gray-7 mb-4">
            <span class="lucide-globe inline mr-1.5" aria-hidden="true" /> Referrers
          </h3>
          <div v-if="!sources.referrers?.length" class="text-sm text-ink-gray-5 py-5 text-center">
            No referrer data yet
          </div>
          <div v-else class="flex flex-col gap-3">
            <div v-for="r in sources.referrers" :key="r.source" class="flex justify-between text-sm">
              <span class="text-ink-gray-7 truncate max-w-[220px]">{{ r.source || "(direct)" }}</span>
              <span class="font-medium text-ink-gray-9">{{ r.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>