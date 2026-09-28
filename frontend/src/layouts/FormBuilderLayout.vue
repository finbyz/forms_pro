<script setup lang="ts">
import { ref } from "vue";
import { useKeyboardShortcuts } from "@/composables/useKeyboardShortcuts";
import FormBuilderHeader from "@/components/FormBuilderHeader.vue";
import FormBuilderSidebar from "@/components/FormBuilderSidebar.vue";
import FormBuilderContent from "@/components/FormBuilderContent.vue";
import FieldEditorSidebar from "@/components/FieldEditorSidebar.vue";
import ThemeEditor from "@/components/studio/design/ThemeEditor.vue";
import FormSettings from "@/components/studio/settings/FormSettings.vue";
import VersionsHistory from "@/components/studio/versions/VersionsHistory.vue";
import AnalyticsPanel from "@/components/studio/AnalyticsPanel.vue";
import { useEditForm } from "@/stores/editForm";

const activeTab = ref("Build");
const editFormStore = useEditForm();

useKeyboardShortcuts();
</script>

<template>
    <div class="flex flex-col h-screen bg-surface-base overflow-hidden">
        <FormBuilderHeader v-model:activeTab="activeTab" />
        <div class="flex flex-1 min-h-0 overflow-hidden">
            <template v-if="activeTab === 'Build'">
                <div class="flex w-full min-h-0 overflow-hidden">
                    <FormBuilderSidebar v-if="editFormStore.activeSectionIndex !== 'success'" />
                    <FormBuilderContent />
                    <FieldEditorSidebar v-if="editFormStore.activeSectionIndex !== 'success'" />
                </div>
            </template>
            <template v-else-if="activeTab === 'Design'">
                <ThemeEditor class="w-full overflow-y-auto" />
            </template>
            <template v-else-if="activeTab === 'Settings'">
                <FormSettings class="w-full overflow-y-auto" />
            </template>
            <template v-else-if="activeTab === 'Versions'">
                <VersionsHistory class="w-full overflow-y-auto" />
            </template>
            <template v-else-if="activeTab === 'Analytics'">
                <AnalyticsPanel class="w-full overflow-y-auto" />
            </template>
        </div>
    </div>
</template>
