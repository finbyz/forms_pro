<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { Button, Badge, createResource, FeatherIcon, Tooltip } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";

const editFormStore = useEditForm();
const summary = ref<any>({ total: 0, success: 0, failed: 0, created: 0, updated: 0, conversion_rate: 0 });
const sources = ref<any>({ utm_sources: [], referrers: [] });
const timeseries = ref<any>({ dates: [], counts: [] });
const loading = ref(false);
const activePreset = ref("30 days");
const hoveredBar = ref<{ date: string; count: number } | null>(null);

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

function applyPreset(preset: { label: string; days: number }) {
  activePreset.value = preset.label;
  const end = new Date();
  const start = preset.days === -1 ? new Date("2020-01-01") : new Date(Date.now() - preset.days * 24 * 60 * 60 * 1000);
  dateRange.value = {
    start: start.toISOString().split("T")[0],
    end: end.toISOString().split("T")[0],
  };
  fetchAnalytics();
}

function onCustomDateChange() {
  activePreset.value = "Custom";
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
  const rows = chartData.value.map((item) => ({
    date: item.date,
    submissions: item.count,
  }));
  const csv = ["Date,Submissions", ...rows.map(r => `${r.date},${r.submissions}`)].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
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
  let convRateDisplay = "0%";
  if (typeof sum.conversion_rate === "number") {
    convRateDisplay = sum.conversion_rate + "%";
  }

  return [
    {
      label: "Total Submissions",
      value: sum.total ?? 0,
      icon: "inbox",
      iconBg: "bg-surface-blue-2 text-ink-blue-7",
      context: "All responses received in range",
      badge: null,
    },
    {
      label: "Successful",
      value: sum.success ?? 0,
      icon: "check-circle",
      iconBg: "bg-surface-green-2 text-ink-green-7",
      context: "Successfully processed",
      badge: { theme: "green", label: "Processed" },
    },
    {
      label: "Failed",
      value: sum.failed ?? 0,
      icon: "alert-circle",
      iconBg: sum.failed > 0 ? "bg-surface-red-2 text-ink-red-7" : "bg-surface-gray-2 text-ink-gray-5",
      context: sum.failed > 0 ? "Requires review" : "No submission errors",
      badge: sum.failed > 0 ? { theme: "red", label: "Issues" } : null,
    },
    {
      label: "Records Created",
      value: sum.created ?? 0,
      icon: "plus-circle",
      iconBg: "bg-surface-purple-2 text-ink-purple-7",
      context: "New documents created in DocType",
      badge: null,
    },
    {
      label: "Records Updated",
      value: sum.updated ?? 0,
      icon: "edit-3",
      iconBg: "bg-surface-teal-2 text-ink-teal-7",
      context: "Existing records updated in DocType",
      badge: null,
    },
    {
      label: "Conversion Rate",
      value: convRateDisplay,
      icon: "trending-up",
      iconBg: "bg-surface-amber-2 text-ink-amber-7",
      context: "Submission completion rate",
      badge: { theme: "amber", label: "Efficiency" },
      progressBar: typeof sum.conversion_rate === "number" ? Math.min(100, Math.max(0, sum.conversion_rate)) : 0,
    },
  ];
});

// Continuous timeline points between start and end
const chartData = computed(() => {
  if (!dateRange.value.start || !dateRange.value.end) return [];

  const countMap: Record<string, number> = {};
  if (timeseries.value.dates && timeseries.value.counts) {
    timeseries.value.dates.forEach((d: string, idx: number) => {
      countMap[d] = timeseries.value.counts[idx] || 0;
    });
  }

  const list: { date: string; displayDate: string; count: number }[] = [];
  const curr = new Date(dateRange.value.start + "T00:00:00");
  const end = new Date(dateRange.value.end + "T00:00:00");

  const diffDays = Math.round((end.getTime() - curr.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays > 365 || diffDays < 0) {
    return (timeseries.value.dates || []).map((d: string, i: number) => ({
      date: d,
      displayDate: d.slice(5),
      count: timeseries.value.counts[i] || 0,
    }));
  }

  while (curr <= end) {
    const y = curr.getFullYear();
    const m = String(curr.getMonth() + 1).padStart(2, "0");
    const d = String(curr.getDate()).padStart(2, "0");
    const dStr = `${y}-${m}-${d}`;
    list.push({
      date: dStr,
      displayDate: `${m}/${d}`,
      count: countMap[dStr] || 0,
    });
    curr.setDate(curr.getDate() + 1);
  }

  return list;
});

const totalRangeSubmissions = computed(() => {
  return chartData.value.reduce((acc, cur) => acc + cur.count, 0);
});

const maxCount = computed(() => {
  const max = Math.max(...chartData.value.map(d => d.count), 0);
  return max > 0 ? max : 5;
});

const totalUtmCount = computed(() => {
  return (sources.value.utm_sources || []).reduce((acc: number, cur: any) => acc + (cur.count || 0), 0) || 1;
});

const totalReferrerCount = computed(() => {
  return (sources.value.referrers || []).reduce((acc: number, cur: any) => acc + (cur.count || 0), 0) || 1;
});
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface-gray-2/50">
    <!-- Header Toolbar -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between px-6 py-4 bg-surface-base border-b border-outline-gray-1 gap-4 shrink-0 shadow-2xs">
      <div class="flex items-center gap-3">
        <div class="size-8 rounded-lg bg-surface-blue-2 text-ink-blue-7 flex items-center justify-center shrink-0">
          <FeatherIcon name="bar-chart-2" class="size-4" />
        </div>
        <div>
          <h2 class="text-base-semibold text-ink-gray-9 leading-tight">Form Analytics</h2>
          <p class="text-xs text-ink-gray-5 mt-0.5">Submissions volume, completion success, and acquisition performance</p>
        </div>
      </div>

      <!-- Controls & Filters -->
      <div class="flex items-center gap-3 flex-wrap sm:flex-nowrap">
        <!-- Preset pills with clean Frappe friendly curves -->
        <nav class="flex items-center p-1 bg-surface-gray-2 rounded-xl border border-outline-gray-1/80 shrink-0 shadow-2xs">
          <button
            v-for="p in presets"
            :key="p.label"
            type="button"
            @click="applyPreset(p)"
            class="px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150"
            :class="
              activePreset === p.label
                ? 'bg-surface-white text-ink-gray-9 shadow-xs font-semibold border border-outline-gray-2/40'
                : 'text-ink-gray-6 hover:text-ink-gray-9 hover:bg-surface-white/60'
            "
          >
            {{ p.label }}
          </button>
        </nav>

        <!-- Date Range picker input -->
        <div class="flex items-center gap-2 bg-surface-base px-3 py-1.5 border border-outline-gray-1/80 rounded-xl shadow-2xs text-xs text-ink-gray-7 hover:border-outline-gray-2 transition-base">
          <FeatherIcon name="calendar" class="w-3.5 h-3.5 text-ink-gray-5 shrink-0" />
          <input
            type="date"
            v-model="dateRange.start"
            @change="onCustomDateChange"
            aria-label="Start date"
            class="text-xs text-ink-gray-8 bg-transparent border-none focus:outline-none p-0 w-24 cursor-pointer"
          />
          <span class="text-ink-gray-4 text-xs font-medium">to</span>
          <input
            type="date"
            v-model="dateRange.end"
            @change="onCustomDateChange"
            aria-label="End date"
            class="text-xs text-ink-gray-8 bg-transparent border-none focus:outline-none p-0 w-24 cursor-pointer"
          />
        </div>

        <!-- Action buttons -->
        <div class="flex items-center gap-2 shrink-0">
          <Tooltip text="Refresh analytics data" placement="bottom">
            <Button
              variant="ghost"
              size="sm"
              icon="refresh-cw"
              :loading="loading"
              @click="fetchAnalytics"
              class="whitespace-nowrap"
            >
              Refresh
            </Button>
          </Tooltip>
          <Tooltip text="Export daily submissions to CSV" placement="bottom">
            <Button
              variant="outline"
              size="sm"
              icon-left="download"
              @click="exportCSV"
              class="whitespace-nowrap"
            >
              Export CSV
            </Button>
          </Tooltip>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      <!-- KPI Cards Grid (3 cols on desktop, 2 on tablet, 1 on mobile) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="kpi in kpis"
          :key="kpi.label"
          class="bg-surface-base rounded-8 border border-outline-gray-1 p-5 shadow-2xs hover:border-outline-gray-2 hover:shadow-xs transition-all duration-200 flex flex-col justify-between"
        >
          <div>
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-ink-gray-5 uppercase tracking-wider">{{ kpi.label }}</span>
              <div :class="['size-8 rounded-6 flex items-center justify-center shrink-0', kpi.iconBg]">
                <FeatherIcon :name="kpi.icon" class="size-4" />
              </div>
            </div>
            <div class="flex items-baseline gap-2 mt-2">
              <span class="text-2xl font-bold text-ink-gray-9 tracking-tight">{{ kpi.value }}</span>
              <Badge v-if="kpi.badge" :theme="kpi.badge.theme" variant="subtle" size="sm">
                {{ kpi.badge.label }}
              </Badge>
            </div>
          </div>

          <div class="mt-3 pt-3 border-t border-outline-gray-1/60">
            <p class="text-2xs text-ink-gray-5">{{ kpi.context }}</p>
            <div v-if="kpi.progressBar !== undefined" class="h-1.5 w-full bg-surface-gray-2 rounded-full overflow-hidden mt-2">
              <div
                class="h-full bg-surface-amber-6 rounded-full transition-all duration-500 ease-out"
                :style="{ width: `${kpi.progressBar}%` }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Timeseries Chart Card -->
      <div class="bg-surface-base rounded-8 border border-outline-gray-1 p-6 shadow-2xs">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-outline-gray-1 gap-2">
          <div>
            <div class="flex items-center gap-2">
              <div class="size-6 rounded-4 bg-surface-blue-2 text-ink-blue-7 flex items-center justify-center shrink-0">
                <FeatherIcon name="trending-up" class="size-3.5" />
              </div>
              <h3 class="text-sm-semibold text-ink-gray-9">Daily Submissions Activity</h3>
            </div>
            <p class="text-xs text-ink-gray-5 mt-0.5 ml-8">
              {{ dateRange.start }} to {{ dateRange.end }}
            </p>
          </div>
          <div class="flex items-center gap-3">
            <Badge variant="subtle" theme="blue" size="md">
              {{ totalRangeSubmissions }} Submission{{ totalRangeSubmissions === 1 ? '' : 's' }} in period
            </Badge>
            <div class="flex items-center gap-1.5 text-2xs text-ink-gray-5">
              <span class="size-2 rounded-full bg-surface-blue-6 inline-block"></span>
              <span>Successful</span>
            </div>
          </div>
        </div>

        <!-- Chart Area -->
        <div class="relative h-64 flex flex-col justify-end pt-6">
          <!-- Hover Detail Banner -->
          <div
            v-if="hoveredBar"
            class="absolute top-0 right-0 bg-surface-gray-2 px-2.5 py-1 rounded-6 text-xs text-ink-gray-8 border border-outline-gray-1 animate-fade-in"
          >
            <span class="font-semibold text-ink-blue-7">{{ hoveredBar.count }}</span> submission{{ hoveredBar.count === 1 ? '' : 's' }} on {{ hoveredBar.date }}
          </div>

          <!-- If completely empty and 0 days -->
          <div v-if="chartData.length === 0" class="flex flex-col items-center justify-center h-full text-center py-10">
            <FeatherIcon name="bar-chart-2" class="size-8 text-ink-gray-4 mb-2" />
            <p class="text-sm-medium text-ink-gray-8">No data for selected date range</p>
            <p class="text-xs text-ink-gray-5 mt-1">Try choosing a wider range or 'All time' above.</p>
          </div>

          <!-- Bars Display -->
          <div v-else class="h-full flex items-end justify-between gap-1 sm:gap-1.5 px-2 pb-1 border-b border-outline-gray-2">
            <div
              v-for="(item, idx) in chartData"
              :key="item.date"
              class="flex-1 flex flex-col items-center h-full justify-end group relative cursor-pointer"
              @mouseenter="hoveredBar = item"
              @mouseleave="hoveredBar = null"
            >
              <!-- Bar -->
              <div class="w-full max-w-[32px] flex flex-col justify-end h-full">
                <div
                  class="w-full rounded-t-4 transition-all duration-200"
                  :class="
                    item.count > 0
                      ? 'bg-surface-blue-6 group-hover:bg-surface-blue-7 shadow-2xs'
                      : 'bg-surface-gray-3/60 group-hover:bg-surface-gray-4'
                  "
                  :style="{
                    height: item.count > 0 ? `${(item.count / maxCount) * 100}%` : '4px',
                    minHeight: '4px',
                  }"
                />
              </div>

              <!-- Floating Tooltip on Hover -->
              <div
                class="opacity-0 group-hover:opacity-100 pointer-events-none absolute -top-8 z-30 transition-opacity bg-ink-gray-9 text-surface-white text-[11px] font-medium px-2 py-0.5 rounded-4 whitespace-nowrap shadow-md"
              >
                {{ item.date }}: {{ item.count }}
              </div>
            </div>
          </div>

          <!-- X-Axis Labels (sampled to prevent clutter) -->
          <div v-if="chartData.length > 0" class="flex justify-between px-2 pt-2 text-[10px] text-ink-gray-5 select-none">
            <span>{{ chartData[0]?.displayDate }}</span>
            <span v-if="chartData.length > 10">{{ chartData[Math.floor(chartData.length / 2)]?.displayDate }}</span>
            <span>{{ chartData[chartData.length - 1]?.displayDate }}</span>
          </div>
        </div>
      </div>

      <!-- Traffic & Referrers Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6">
        <!-- UTM Sources -->
        <div class="bg-surface-base rounded-8 border border-outline-gray-1 p-5 shadow-2xs">
          <div class="flex items-center justify-between pb-3 border-b border-outline-gray-1">
            <div class="flex items-center gap-2">
              <div class="size-7 rounded-6 bg-surface-blue-2 text-ink-blue-7 flex items-center justify-center shrink-0">
                <FeatherIcon name="compass" class="size-4" />
              </div>
              <div>
                <h4 class="text-sm-semibold text-ink-gray-9">UTM Sources</h4>
                <p class="text-2xs text-ink-gray-5">Campaign acquisition breakdown</p>
              </div>
            </div>
            <Badge v-if="sources.utm_sources?.length" variant="subtle" theme="blue" size="sm">
              {{ sources.utm_sources.length }} Detected
            </Badge>
          </div>

          <div v-if="!sources.utm_sources?.length" class="flex flex-col items-center justify-center py-10 text-center">
            <div class="size-10 rounded-full bg-surface-gray-2 flex items-center justify-center mb-2">
              <FeatherIcon name="tag" class="size-5 text-ink-gray-4" />
            </div>
            <p class="text-xs-semibold text-ink-gray-8">No campaign tags captured</p>
            <p class="text-2xs text-ink-gray-5 max-w-xs mt-1">
              Add <code class="bg-surface-gray-2 px-1 py-0.5 rounded font-mono text-ink-gray-7">?utm_source=...</code> to your form link to track acquisition.
            </p>
          </div>
          <div v-else class="space-y-3 pt-4">
            <div v-for="s in sources.utm_sources" :key="s.source" class="space-y-1">
              <div class="flex justify-between items-center text-xs">
                <span class="font-medium text-ink-gray-8 truncate max-w-[220px]">{{ s.source || "(direct)" }}</span>
                <span class="font-semibold text-ink-gray-9">{{ s.count }}</span>
              </div>
              <div class="h-1.5 w-full bg-surface-gray-2 rounded-full overflow-hidden">
                <div
                  class="h-full bg-surface-blue-6 rounded-full"
                  :style="{ width: `${(s.count / totalUtmCount) * 100}%` }"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Referrers -->
        <div class="bg-surface-base rounded-8 border border-outline-gray-1 p-5 shadow-2xs">
          <div class="flex items-center justify-between pb-3 border-b border-outline-gray-1">
            <div class="flex items-center gap-2">
              <div class="size-7 rounded-6 bg-surface-green-2 text-ink-green-7 flex items-center justify-center shrink-0">
                <FeatherIcon name="globe" class="size-4" />
              </div>
              <div>
                <h4 class="text-sm-semibold text-ink-gray-9">Referrers</h4>
                <p class="text-2xs text-ink-gray-5">Originating domains and websites</p>
              </div>
            </div>
            <Badge v-if="sources.referrers?.length" variant="subtle" theme="green" size="sm">
              {{ sources.referrers.length }} Detected
            </Badge>
          </div>

          <div v-if="!sources.referrers?.length" class="flex flex-col items-center justify-center py-10 text-center">
            <div class="size-10 rounded-full bg-surface-gray-2 flex items-center justify-center mb-2">
              <FeatherIcon name="link-2" class="size-5 text-ink-gray-4" />
            </div>
            <p class="text-xs-semibold text-ink-gray-8">No external referrers</p>
            <p class="text-2xs text-ink-gray-5 max-w-xs mt-1">
              Submissions were accessed directly without an external referrer.
            </p>
          </div>
          <div v-else class="space-y-3 pt-4">
            <div v-for="r in sources.referrers" :key="r.source" class="space-y-1">
              <div class="flex justify-between items-center text-xs">
                <span class="font-medium text-ink-gray-8 truncate max-w-[220px]">{{ r.source || "(direct)" }}</span>
                <span class="font-semibold text-ink-gray-9">{{ r.count }}</span>
              </div>
              <div class="h-1.5 w-full bg-surface-gray-2 rounded-full overflow-hidden">
                <div
                  class="h-full bg-surface-green-6 rounded-full"
                  :style="{ width: `${(r.count / totalReferrerCount) * 100}%` }"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>