<script setup lang="ts">
import { ref } from "vue";
import { useKeyboardShortcuts } from "@/composables/useKeyboardShortcuts";
import FormBuilderHeader from "@/components/FormBuilderHeader.vue";
import FormBuilderSidebar from "@/components/FormBuilderSidebar.vue";
import FormBuilderContent from "@/components/FormBuilderContent.vue";
import FieldEditorSidebar from "@/components/FieldEditorSidebar.vue";
import SuccessCanvas from "@/components/studio/success/SuccessCanvas.vue";
import ThemeEditor from "@/components/studio/design/ThemeEditor.vue";
import FormSettings from "@/components/studio/settings/FormSettings.vue";
import SubmissionsBrowser from "@/components/studio/submissions/SubmissionsBrowser.vue";
import VersionsHistory from "@/components/studio/versions/VersionsHistory.vue";
import AnalyticsPanel from "@/components/studio/AnalyticsPanel.vue";

const activeTab = ref("Build");

useKeyboardShortcuts();
</script>

<template>
    <div class="flex flex-col h-screen bg-surface-base">
        <FormBuilderHeader v-model:activeTab="activeTab" />
        <div class="flex flex-1 overflow-hidden">
            <template v-if="activeTab === 'Build'">
                <div class="flex w-full overflow-hidden">
                    <FormBuilderSidebar />
                    <FormBuilderContent />
                    <FieldEditorSidebar />
                </div>
            </template>
            <template v-else-if="activeTab === 'Success'">
                <SuccessCanvas class="w-full" />
            </template>
            <template v-else-if="activeTab === 'Design'">
                <ThemeEditor class="w-full" />
            </template>
            <template v-else-if="activeTab === 'Settings'">
                <FormSettings class="w-full" />
            </template>
            <template v-else-if="activeTab === 'Submissions'">
                <SubmissionsBrowser class="w-full" />
            </template>
            <template v-else-if="activeTab === 'Versions'">
                <VersionsHistory class="w-full" />
            </template>
            <template v-else-if="activeTab === 'Analytics'">
                <AnalyticsPanel class="w-full" />
            </template>
        </div>
    </div>
</template>
