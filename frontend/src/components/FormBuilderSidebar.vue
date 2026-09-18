<script setup lang="ts">
import { computed, ref } from "vue";
import { Tooltip, Button } from "frappe-ui";
import AddFieldsSection from "@/components/builder/sidebar/AddFieldsSection.vue";
import SettingsSection from "@/components/builder/sidebar/SettingsSection.vue";
import DocTypeFieldsSection from "@/components/builder/sidebar/DoctypeFieldsSection.vue";

const sidebarSections = [
    {
        id: "settings",
        label: "Settings",
        icon: "lucide-settings",
        section: SettingsSection,
    },
    {
        id: "add-fields",
        label: "Add Fields",
        icon: "lucide-plus",
        section: AddFieldsSection,
    },
    {
        id: "doctype-fields",
        label: "DocType Fields",
        icon: "lucide-stretch-horizontal",
        section: DocTypeFieldsSection,
    },
];

const activeSection = ref(
    sidebarSections.find((s) => s.id === "add-fields") ?? sidebarSections[0]
);

const tabId = (id: string) => `form-builder-tab-${id}`;
const panelId = (id: string) => `form-builder-panel-${id}`;
const activeTabId = computed(() => tabId(activeSection.value.id));
const activePanelId = computed(() => panelId(activeSection.value.id));
</script>
<template>
    <div
        class="h-full w-[320px] border-r border-outline-gray-1 flex bg-surface-base"
        data-form-builder-component="form-builder-sidebar"
    >
        <!-- Tab Navigation -->
        <div
            role="tablist"
            aria-label="Form builder sections"
            aria-orientation="vertical"
            class="h-full flex flex-col gap-1 p-3 border-r border-outline-gray-1 shrink-0 bg-surface-base"
        >
            <Tooltip
                v-for="section in sidebarSections"
                :key="section.id"
                :text="section.label"
                placement="right"
            >
                <div class="relative">
                    <span
                        v-if="activeSection.id === section.id"
                        aria-hidden="true"
                        class="absolute -left-3 top-1/2 -translate-y-1/2 h-8 w-1 rounded-full bg-surface-gray-9"
                    />
                    <Button
                        size="md"
                        role="tab"
                        :id="tabId(section.id)"
                        :aria-label="section.label"
                        :aria-selected="activeSection.id === section.id"
                        :aria-controls="panelId(section.id)"
                        @click="activeSection = section"
                        :variant="activeSection.id === section.id ? 'subtle' : 'ghost'"
                        theme="gray"
                        class="w-full justify-center active:scale-98 transition-base"
                        :icon="section.icon"
                    />
                </div>
            </Tooltip>
        </div>

        <!-- Tab Content -->
        <div
            role="tabpanel"
            :id="activePanelId"
            :aria-labelledby="activeTabId"
            tabindex="0"
            class="flex flex-col flex-1 min-w-0 overflow-y-auto overflow-x-hidden focus:outline-none focus-visible:focus-ring"
        >
            <div class="p-6 space-y-6">
                <Transition name="section-fade" mode="out-in">
                    <component :is="activeSection.section" :key="activeSection.id" />
                </Transition>
            </div>
        </div>
    </div>
</template>

<style scoped>
.section-fade-enter-active {
    transition: opacity 200ms ease-out;
}
.section-fade-leave-active {
    transition: opacity 150ms ease-in;
}
.section-fade-enter-from,
.section-fade-leave-to {
    opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
    .section-fade-enter-active,
    .section-fade-leave-active {
        transition: none;
    }
}
</style>
