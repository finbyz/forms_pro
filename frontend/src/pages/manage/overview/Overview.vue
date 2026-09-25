<script setup lang="ts">
import { computed } from "vue";
import { Breadcrumbs, TabButtons } from "frappe-ui";
import { useManageForm } from "@/stores/form/manageForm";
import { useQueryParam } from "@/composables/useQueryParam";
import OverviewHero from "@/components/form/manage/OverviewHero.vue";
import QuickShareCard from "@/components/form/manage/QuickShareCard.vue";
import OverviewMetrics from "@/components/form/manage/OverviewMetrics.vue";
import RecentSubmissionsWidget from "@/components/form/manage/RecentSubmissionsWidget.vue";
import FormConfigSummary from "@/components/form/manage/FormConfigSummary.vue";
import AccessSection from "@/components/form/manage/AccessSection.vue";
import ShareEmbedSection from "@/components/form/manage/ShareEmbedSection.vue";
import FieldsSummarySection from "@/components/form/manage/FieldsSummarySection.vue";

const manageFormStore = useManageForm();

const breadcrumbItems = computed(() => [
    { label: "Forms", to: "/" },
    { label: "Manage Form", to: `/manage/${manageFormStore.currentFormId}/overview` },
    { label: manageFormStore.formData?.title || "Overview" },
]);

const tabs = [
    {
        label: "Overview",
        iconLeft: "lucide-layout-grid",
        value: "overview",
    },
    {
        label: "Access",
        iconLeft: "lucide-lock",
        value: "shared",
    },
    {
        label: "Share & Embed",
        iconLeft: "lucide-code",
        value: "embed",
    },
    {
        label: "Fields",
        iconLeft: "lucide-sliders",
        value: "fields",
    },
] as const;

type TabValue = (typeof tabs)[number]["value"];
const validTabValues: TabValue[] = tabs.map((t) => t.value);
const selectedTab = useQueryParam<TabValue>("tab", "overview", validTabValues);

function handleOpenShareTab() {
    selectedTab.value = "embed";
}
</script>

<template>
    <div class="flex flex-col gap-5 w-full pb-12">
        <!-- Breadcrumbs Navigation -->
        <Breadcrumbs :items="breadcrumbItems" class="text-xs" />

        <!-- Form Hero Header -->
        <div v-if="manageFormStore.formData" class="flex flex-col gap-5">
            <OverviewHero />

            <!-- Tab Navigation Bar -->
            <div class="flex items-center justify-between gap-4 border-b border-outline-gray-1 pb-1">
                <TabButtons
                    class="w-fit"
                    :buttons="tabs"
                    v-model="selectedTab"
                />
            </div>

            <!-- TAB 1: OVERVIEW / DASHBOARD -->
            <div v-if="selectedTab === 'overview'" class="flex flex-col gap-5 animate-in fade-in duration-200">
                <!-- Quick Share Bar -->
                <QuickShareCard @open-share-tab="handleOpenShareTab" />

                <!-- KPI Metric Cards Grid -->
                <OverviewMetrics />

                <!-- 2-Column Responsive Layout -->
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
                    <!-- Left Column (2 spans): Recent Submissions & Description -->
                    <div class="lg:col-span-2 flex flex-col gap-5">
                        <!-- Recent Submissions Widget -->
                        <RecentSubmissionsWidget />

                        <!-- Form Description & Instructions Card -->
                        <div class="bg-surface-base border border-outline-gray-1 rounded-8 p-4 flex flex-col gap-2">
                            <div class="flex items-center justify-between pb-2 border-b border-outline-gray-1">
                                <h4 class="text-sm font-semibold text-ink-gray-9 flex items-center gap-2">
                                    <lucide-file-text class="size-4 text-ink-gray-6" aria-hidden="true" />
                                    Description & Instructions
                                </h4>
                            </div>
                            <div
                                v-if="manageFormStore.formData?.description"
                                class="prose prose-sm text-ink-gray-7 max-w-none mt-1 leading-relaxed"
                                v-html="manageFormStore.formData.description"
                            ></div>
                            <div v-else class="text-xs text-ink-gray-4 italic py-2">
                                No description provided for this form. You can add one in the Form Builder Studio.
                            </div>
                        </div>
                    </div>

                    <!-- Right Column (1 span): Form Config & Quick Links -->
                    <div class="flex flex-col gap-5">
                        <FormConfigSummary />
                    </div>
                </div>
            </div>

            <!-- TAB 2: ACCESS & PERMISSIONS -->
            <div v-else-if="selectedTab === 'shared'" class="animate-in fade-in duration-200">
                <AccessSection />
            </div>

            <!-- TAB 3: SHARE & EMBED -->
            <div v-else-if="selectedTab === 'embed'" class="animate-in fade-in duration-200">
                <ShareEmbedSection />
            </div>

            <!-- TAB 4: FIELDS & SCHEMA -->
            <div v-else-if="selectedTab === 'fields'" class="animate-in fade-in duration-200">
                <FieldsSummarySection />
            </div>
        </div>

        <!-- Skeleton Loading State -->
        <div v-else class="flex flex-col gap-4 py-8 animate-pulse">
            <div class="h-8 w-48 bg-surface-gray-2 rounded-6"></div>
            <div class="h-24 w-full bg-surface-gray-2 rounded-8"></div>
            <div class="grid grid-cols-4 gap-4">
                <div class="h-24 bg-surface-gray-2 rounded-8"></div>
                <div class="h-24 bg-surface-gray-2 rounded-8"></div>
                <div class="h-24 bg-surface-gray-2 rounded-8"></div>
                <div class="h-24 bg-surface-gray-2 rounded-8"></div>
            </div>
        </div>
    </div>
</template>
