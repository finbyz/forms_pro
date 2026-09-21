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
        <!-- Tab Navigation (Horizontal) -->
        <div
            role="tablist"
            aria-label="Form builder sections"
            class="flex items-center w-full px-4 pt-4 border-b border-outline-gray-1 bg-surface-base gap-4"
        >
            <button
                v-for="section in sidebarSections"
                :key="section.id"
                role="tab"
                :id="tabId(section.id)"
                :aria-selected="activeSection.id === section.id"
                :aria-controls="panelId(section.id)"
                class="pb-2 text-sm font-medium transition-colors border-b-2 relative -mb-[1px]"
                :class="activeSection.id === section.id ? 'border-ink-gray-9 text-ink-gray-9' : 'border-transparent text-ink-gray-5 hover:text-ink-gray-7'"
                @click="activeSection = section"
            >
                {{ section.label }}
            </button>
        </div>

        <!-- Tab Content Panels -->
        <div class="flex-1 overflow-y-auto">
            <template v-for="section in sidebarSections" :key="section.id">
                <div
                    v-show="activeSection.id === section.id"
                    role="tabpanel"
                    :id="panelId(section.id)"
                    :aria-labelledby="tabId(section.id)"
                    class="h-full p-4"
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
