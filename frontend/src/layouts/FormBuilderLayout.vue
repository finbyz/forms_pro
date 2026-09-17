<script setup lang="ts">
import { ref } from "vue";
import FormBuilderHeader from "@/components/FormBuilderHeader.vue";
import FormBuilderSidebar from "@/components/FormBuilderSidebar.vue";
import FormBuilderContent from "@/components/FormBuilderContent.vue";
import FieldEditorSidebar from "@/components/FieldEditorSidebar.vue";

const activeTab = ref("Build");
</script>
<template>
    <div class="flex flex-col h-screen">
        <FormBuilderHeader v-model:activeTab="activeTab" />
        <div class="flex flex-1 overflow-hidden">
            <template v-if="activeTab === \"Build\"">
                <div class="flex gap-4 justify-between w-full overflow-hidden">
                    <FormBuilderSidebar />
                    <FormBuilderContent />
                    <FieldEditorSidebar />
                </div>
            </template>
            <template v-else-if="activeTab === \"Success\"">
                <div class="flex flex-col w-full items-center justify-center bg-gray-50 text-gray-500">
                    <div class="text-xl font-medium mb-2">Success Page Designer</div>
                    <div>Visual designer for form submission success pages.</div>
                </div>
            </template>
            <template v-else-if="activeTab === \"Design\"">
                <div class="flex flex-col w-full items-center justify-center bg-gray-50 text-gray-500">
                    <div class="text-xl font-medium mb-2">Theme Designer</div>
                    <div>Design system tokens, typography, and colors.</div>
                </div>
            </template>
            <template v-else-if="activeTab === \"Settings\"">
                <div class="flex flex-col w-full items-center justify-center bg-gray-50 text-gray-500">
                    <div class="text-xl font-medium mb-2">Form Settings</div>
                    <div>Target doctype strategy, Access, Embed allowed origins.</div>
                </div>
            </template>
        </div>
    </div>
</template>
