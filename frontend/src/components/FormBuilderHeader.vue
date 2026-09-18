<script setup lang="ts">
import { Tabs, Badge, Button, Popover, Tooltip, type ButtonProps } from "frappe-ui";
import { TextMorph } from "torph/vue";
import { useEditForm } from "@/stores/editForm";
import { useRouter } from "vue-router";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import Logo from "@/assets/Logo.vue";
import FormActions from "@/components/studio/actions/FormActions.vue";
import PreviewDialog from "@/components/builder/PreviewDialog.vue";
import { ChevronDown, ArrowLeft, CloudCheck, CloudOff, ExternalLink, Play, MoreHorizontal } from "@lucide/vue";

const router = useRouter();
const editFormStore = useEditForm();
const showPreview = ref(false);

const props = defineProps<{ activeTab: string }>();
const emit = defineEmits<{ (e: "update:activeTab", value: string): void }>();

const SUBMISSION_ROUTE_NAME = "Form Submission Page";
const TABS = ["Build", "Success", "Design", "Settings", "Submissions", "Versions", "Analytics"] as const;

const tabObjects = TABS.map(t => ({ label: t, value: t }));
const tabIndex = computed({
    get: () => TABS.indexOf(props.activeTab as any),
    set: (idx) => emit("update:activeTab", TABS[idx])
});

type ActionConfig = {
    label: string;
    iconLeft: string;
    variant: ButtonProps["variant"];
    theme: ButtonProps["theme"];
    handler: () => unknown;
};

function computeConfig(): ActionConfig {
    if (editFormStore.isUnsaved && editFormStore.isPublished)
        return { label: "Save and publish", iconLeft: "lucide-globe", variant: "solid", theme: "gray", handler: editFormStore.saveAndPublish };
    if (editFormStore.isUnsaved)
        return { label: "Save", iconLeft: "", variant: "solid", theme: "gray", handler: editFormStore.save };
    if (editFormStore.isPublished)
        return { label: "Unpublish", iconLeft: "", variant: "subtle", theme: "red", handler: editFormStore.togglePublish };
    return { label: "Publish", iconLeft: "lucide-globe", variant: "solid", theme: "gray", handler: editFormStore.togglePublish };
}

const frozenConfig = ref<ActionConfig | null>(null);
const buttonConfig = computed<ActionConfig>(() => frozenConfig.value ?? computeConfig());
watch(() => editFormStore.formResource, (r) => { if (!r) frozenConfig.value = null; });

const morphLabel = ref("");
onMounted(() => { morphLabel.value = buttonConfig.value.label; });
watch(() => buttonConfig.value.label, (l) => { morphLabel.value = l; });

async function onAction() {
    if (frozenConfig.value) return;
    frozenConfig.value = computeConfig();
    try {
        await frozenConfig.value.handler();
        await nextTick();
    } catch {
        // handled by store
    } finally {
        frozenConfig.value = null;
    }
}

const openFormSubmissionPage = () => {
    const route = editFormStore.originalFormData?.route;
    if (!route) return;
    const routeRecord = router.getRoutes().find((r) => r.name === SUBMISSION_ROUTE_NAME);
    if (!routeRecord) return;
    const path = routeRecord.path.replace(/:\w+\(.*?\)/, route);
    window.open(router.resolve(path).href, "_blank");
};
</script>

<template>
    <header class="flex flex-col bg-surface-base border-b border-outline-gray-1 sticky top-0 z-50" data-form-builder-component="form-builder-header">
        <!-- Title row -->
        <div class="flex justify-between items-center px-6 h-14 border-b border-outline-gray-1">
            <div class="flex items-center gap-4 min-w-0 flex-1">
<Popover>
    <template #target="{ togglePopover }">
        <button 
            class="flex items-center gap-2 hover:bg-surface-gray-2 active:bg-surface-gray-3 active:scale-98 transition-base rounded-4 px-2 py-1.5 -ml-2 focus-visible:outline-none focus-visible:focus-ring" 
            @click="togglePopover"
            aria-label="Navigation menu"
        >
            <Logo />
            <ChevronDown class="w-5 h-5 text-ink-gray-6" aria-hidden="true" />
        </button>
    </template>
    <template #body-main>
        <div class="p-1 min-w-[200px]">
            <Button 
                label="Go Back" 
                icon-left="arrow-left" 
                variant="ghost" 
                size="sm"
                @click="router.replace({ name: 'Manage Form', params: { id: editFormStore.originalFormData?.name } })" 
            />
        </div>
    </template>
</Popover>

<div class="h-6 w-px bg-outline-gray-1" aria-hidden="true" />

<div class="flex items-center gap-3 min-w-0 flex-1">
    <Badge v-if="editFormStore.isUnsaved" variant="subtle" label="Unsaved" theme="amber" size="sm" />
    <Tooltip v-else-if="editFormStore.isPublished" text="Form is published" placement="bottom">
        <CloudCheck class="w-4 h-4 text-green-600" />
    </Tooltip>
    <Tooltip v-else text="Form is not published" placement="bottom">
        <CloudOff class="w-4 h-4 text-gray-500" />
    </Tooltip>
                    <h1 class="text-base-semibold text-ink-gray-9 truncate">
                        {{ editFormStore.originalFormData?.title || "Untitled Form" }}
                    </h1>
                    <div v-if="editFormStore.originalFormData?.route" class="flex items-center gap-1.5 shrink-0">
                        <span class="text-sm text-ink-gray-5 truncate max-w-[200px]">
                            /{{ editFormStore.originalFormData?.route }}
                        </span>
                        <Tooltip text="Open in new tab" placement="bottom">
                            <Button variant="ghost" size="sm" icon="lucide-external-link" @click="openFormSubmissionPage" />
                        </Tooltip>
                    </div>
                </div>
            </div>

            <div class="flex items-center gap-2 shrink-0">
                <Tooltip text="Preview" placement="bottom">
                    <Button variant="ghost" size="sm" icon="lucide-play" @click="showPreview = true" />
                </Tooltip>
                <Popover>
                    <template #target="{ togglePopover }">
                        <Tooltip text="More actions" placement="bottom">
                            <Button variant="ghost" size="sm" icon="lucide-more-horizontal" @click="togglePopover" />
                        </Tooltip>
                    </template>
                    <template #body-main>
                        <div class="p-1 min-w-[200px]">
                            <FormActions />
                        </div>
                    </template>
                </Popover>
                <div class="h-6 w-px bg-outline-gray-1 mx-1" aria-hidden="true" />
                <Button
                    :aria-label="buttonConfig.label"
                    :icon-left="buttonConfig.iconLeft"
                    :variant="buttonConfig.variant"
                    :theme="buttonConfig.theme"
                    :loading="editFormStore.isSaving || editFormStore.isLoading"
                    size="sm"
                    @click="onAction"
                >
                    <TextMorph :text="morphLabel" />
                </Button>
            </div>
        </div>

        <!-- Tab bar -->
        <div class="px-6 bg-surface-base">
            <Tabs
                v-model="tabIndex"
                :tabs="tabObjects"
                variant="underline"
                size="sm"
            />
        </div>
    </header>
    <PreviewDialog :show="showPreview" @close="showPreview = false" />
</template>
