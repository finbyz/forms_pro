<script setup lang="ts">
import { computed, ref } from "vue";
import AddFieldsSection from "@/components/builder/sidebar/AddFieldsSection.vue";
import SettingsSection from "@/components/builder/sidebar/SettingsSection.vue";
import DocTypeFieldsSection from "@/components/builder/sidebar/DoctypeFieldsSection.vue";

const sidebarSections = [
    {
        id: "add-fields",
        label: "Fields",
        section: AddFieldsSection,
    },
    {
        id: "doctype-fields",
        label: "DocType",
        section: DocTypeFieldsSection,
    },
    {
        id: "settings",
        label: "Logic",
        section: SettingsSection,
    }
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
        class="h-full w-[300px] border-r border-outline-gray-1 flex flex-col bg-surface-base shrink-0"
        data-form-builder-component="form-builder-sidebar"
    >
        <!-- Tab Navigation (Segmented pill control with clean Frappe friendly curves) -->
        <div class="px-3 pt-3 pb-2 border-b border-outline-gray-1 bg-surface-base">
            <div
                role="tablist"
                aria-label="Form builder sections"
                class="flex items-center p-1 bg-surface-gray-2 rounded-xl border border-outline-gray-1/80 shadow-2xs"
            >
                <button
                    v-for="section in sidebarSections"
                    :key="section.id"
                    role="tab"
                    :id="tabId(section.id)"
                    :aria-selected="activeSection.id === section.id"
                    :aria-controls="panelId(section.id)"
                    class="flex-1 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 text-center"
                    :class="
                        activeSection.id === section.id
                            ? 'bg-surface-white text-ink-gray-9 shadow-xs font-semibold border border-outline-gray-2/40'
                            : 'text-ink-gray-6 hover:text-ink-gray-9 hover:bg-surface-white/60'
                    "
                    @click="activeSection = section"
                >
                    {{ section.label }}
                </button>
            </div>
        </div>

        <!-- Tab Content Panels -->
        <div class="flex-1 min-h-0 overflow-y-auto">
            <template v-for="section in sidebarSections" :key="section.id">
                <div
                    v-show="activeSection.id === section.id"
                    role="tabpanel"
                    :id="panelId(section.id)"
                    :aria-labelledby="tabId(section.id)"
                    class="p-4"
                >
                    <component :is="section.section" />
                </div>
            </template>
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
