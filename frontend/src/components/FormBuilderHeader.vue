<script setup lang="ts">
import { Button, Dropdown, Tooltip, createResource } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import { useRouter } from "vue-router";
import { computed, ref, onMounted, onBeforeUnmount } from "vue";
import { toast } from "vue-sonner";
import Logo from "@/assets/Logo.vue";
import PreviewDialog from "@/components/builder/PreviewDialog.vue";

const router = useRouter();
const editFormStore = useEditForm();
const showPreview = ref(false);

const props = defineProps<{ activeTab: string }>();
const emit = defineEmits<{ (e: "update:activeTab", value: string): void }>();

const SUBMISSION_ROUTE_NAME = "Form Submission Page";
const TABS = ["Build", "Design", "Settings", "Versions", "Analytics"] as const;

const tabIndex = computed({
    get: () => {
        const i = TABS.indexOf(props.activeTab as (typeof TABS)[number]);
        return i === -1 ? 0 : i;
    },
    set: (idx) => emit("update:activeTab", TABS[idx])
});

function goBack() {
    const id = editFormStore.originalFormData?.name;
    if (id) router.replace({ name: "Manage Form", params: { id } });
    else router.replace({ name: "Dashboard" });
}

const isSaving = computed(() => editFormStore.isSaving);
const isDirty = computed(() => editFormStore.isUnsaved);
const isPublished = computed(() => editFormStore.isPublished);

// Saving only touches the draft now — visitors keep seeing the published
// snapshot until "Update published form" is pressed.
const hasUnpublishedChanges = computed(() => editFormStore.hasUnpublishedChanges);
const isPublishing = ref(false);

/**
 * One status, one action.
 *
 * The draft saves itself, so save state is reported as a quiet phrase rather
 * than a button — a "Save" button you never need to press is just noise. The
 * publish button only appears when pressing it would actually do something;
 * when the live form already matches the draft there is nothing to say beyond
 * "Published".
 */
const saveStatus = computed(() => {
    if (isSaving.value) return "Saving…";
    if (isDirty.value) return "Unsaved";
    return "Saved";
});

const saveTooltip = computed(() => {
    if (isSaving.value) return "Saving your draft…";
    if (isDirty.value) return "Your draft saves automatically — ⌘S to save now";
    return "All changes saved to your draft";
});

const needsPublish = computed(
    () => !isPublished.value || hasUnpublishedChanges.value
);

const publishLabel = computed(() =>
    isPublished.value ? "Publish changes" : "Publish"
);

const publishTooltip = computed(() => {
    if (!isPublished.value) return "Make this form publicly available";
    return "Visitors still see the previous version — press to push your changes live";
});

async function onPublish() {
    if (isPublishing.value) return;
    if (isPublished.value && !hasUnpublishedChanges.value) return;
    isPublishing.value = true;
    try {
        await editFormStore.publish();
    } catch {
        // store surfaces the error
    } finally {
        isPublishing.value = false;
    }
}

async function onUnpublish() {
    if (isPublishing.value) return;
    isPublishing.value = true;
    try {
        await editFormStore.unpublish();
    } catch {
        // store surfaces the error
    } finally {
        isPublishing.value = false;
    }
}

async function onSave() {
    if (!isDirty.value || isSaving.value) return;
    try {
        await editFormStore.save();
    } catch {
        // store surfaces the error
    }
}

// The draft autosaves, but ⌘S / Ctrl+S is muscle memory — honour it rather
// than letting the browser open a save-page dialog over the builder.
function onSaveShortcut(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        onSave();
    }
}
onMounted(() => window.addEventListener("keydown", onSaveShortcut));
onBeforeUnmount(() => window.removeEventListener("keydown", onSaveShortcut));

const openFormSubmissionPage = () => {
    const route = editFormStore.originalFormData?.route;
    if (!route) return;
    const routeRecord = router.getRoutes().find((r) => r.name === SUBMISSION_ROUTE_NAME);
    if (!routeRecord) return;
    const path = routeRecord.path.replace(/:\w+\(.*?\)/, route);
    window.open(router.resolve(path).href, "_blank");
};

const duplicating = ref(false);
const archiving = ref(false);

async function duplicateForm() {
    const name = editFormStore.originalFormData?.name;
    if (!name) return;
    duplicating.value = true;
    try {
        const res = await createResource({
            url: "forms_pro.api.v1.builder.data.duplicate_form",
            method: "POST",
            makeParams() {
                return { form_name: name };
            },
        }).submit();
        const newName = res?.name;
        const newTitle = res?.title;
        if (newName) {
            toast.success(`"${newTitle}" created.`);
            router.push({ name: "Edit Form", params: { id: newName } });
        }
    } catch {
        toast.error("Duplication failed.");
    } finally {
        duplicating.value = false;
    }
}

async function archiveForm() {
    const name = editFormStore.originalFormData?.name;
    if (!name || !confirm("Archive this form? It will be hidden from public routes.")) return;
    archiving.value = true;
    try {
        await createResource({
            url: "forms_pro.api.v1.builder.data.archive_form",
            method: "POST",
            makeParams() {
                return { form_name: name };
            },
        }).submit();
        toast.warning("Form archived.");
        router.push({ name: "Home" });
    } catch {
        toast.error("Archive failed.");
    } finally {
        archiving.value = false;
    }
}

// Unpublish lives here rather than in the header: it is rare and destructive,
// and sitting next to Publish it was mostly a chance to hit the wrong one.
const moreDropdownOptions = computed(() => [
    ...(editFormStore.originalFormData?.route
        ? [{ label: "Open live form", icon: "external-link", onClick: openFormSubmissionPage }]
        : []),
    {
        label: "Duplicate",
        icon: "copy",
        onClick: duplicateForm,
    },
    ...(isPublished.value
        ? [{ label: "Unpublish", icon: "cloud-off", theme: "red", onClick: onUnpublish }]
        : []),
    {
        label: "Archive",
        icon: "archive",
        theme: "red",
        onClick: archiveForm,
    },
]);
</script>

<template>
    <header class="bg-surface-base border-b border-outline-gray-1 sticky top-0 z-20 shrink-0" data-form-builder-component="form-builder-header">
        <!--
            Three parts, with the outer two sharing the leftover width equally
            (`flex-1 basis-0`) so the tabs sit in the middle of the header
            rather than the middle of whatever space is left. `justify-between`
            alone moved them rightwards as the form name grew, which is why a
            long title pushed the tabs off centre.
        -->
        <div class="flex items-center px-4 sm:px-6 h-14 gap-3">
            <!-- Left: Back, Logo, Form Title -->
            <div class="flex flex-1 basis-0 items-center gap-3 min-w-0">
                <!-- Back -->
                <Tooltip text="Back to form overview" placement="bottom">
                    <Button
                        variant="ghost"
                        size="sm"
                        icon="arrow-left"
                        aria-label="Back to form overview"
                        class="-ml-2 shrink-0"
                        @click="goBack"
                    />
                </Tooltip>

                <!-- Logo -->
                <button
                    class="flex items-center shrink-0 hover:bg-surface-gray-2 active:bg-surface-gray-3 transition-base rounded-4 px-2 py-1.5 focus-visible:outline-none focus-visible:focus-ring"
                    aria-label="All forms"
                    @click="router.push({ name: 'Dashboard' })"
                >
                    <Logo />
                </button>

                <!-- Vertical divider -->
                <div class="h-5 w-px bg-outline-gray-1 shrink-0" aria-hidden="true" />

                <!-- Form title + status + route -->
                <div class="flex items-center gap-2 min-w-0">
                    <h1 class="text-sm-semibold text-ink-gray-9 truncate max-w-[120px] md:max-w-[200px] lg:max-w-[260px]">
                        {{ editFormStore.originalFormData?.title || "Untitled Form" }}
                    </h1>
                    <Tooltip
                        v-if="editFormStore.originalFormData?.route"
                        text="Open live form"
                        placement="bottom"
                    >
                        <button
                            type="button"
                            class="hidden xl:inline-flex max-w-[160px] items-center rounded px-1.5 py-0.5 text-xs text-ink-gray-5 transition-colors hover:bg-surface-gray-2 hover:text-ink-gray-7 focus-visible:outline-none focus-visible:focus-ring"
                            @click="openFormSubmissionPage"
                        >
                            <span class="truncate">/{{ editFormStore.originalFormData?.route }}</span>
                        </button>
                    </Tooltip>
                </div>
            </div>

            <!-- Center: Studio Navigation Tabs (Centered segmented control with clean Frappe friendly radius curves) -->
            <nav class="hidden sm:flex items-center p-1 bg-surface-gray-2 rounded-xl border border-outline-gray-1/80 shrink-0 shadow-2xs">
                <button
                    v-for="(t, idx) in TABS"
                    :key="t"
                    type="button"
                    @click="tabIndex = idx"
                    class="px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all duration-150"
                    :class="
                        tabIndex === idx
                            ? 'bg-surface-white text-ink-gray-9 shadow-xs font-semibold border border-outline-gray-2/40'
                            : 'text-ink-gray-6 hover:text-ink-gray-9 hover:bg-surface-white/60'
                    "
                >
                    {{ t }}
                </button>
            </nav>

            <!-- Right side actions -->
            <div class="flex flex-1 basis-0 items-center justify-end gap-2 min-w-0">
                <Tooltip text="Preview" placement="bottom">
                    <Button variant="ghost" size="sm" icon="play" @click="showPreview = true" />
                </Tooltip>
                <Dropdown
                    :button="{
                        icon: 'more-horizontal',
                        variant: 'ghost',
                        size: 'sm',
                    }"
                    placement="right"
                    :options="moreDropdownOptions"
                />
                <div class="h-5 w-px bg-outline-gray-1 mx-1 shrink-0" aria-hidden="true" />

                <!-- Draft state: one quiet phrase, never a button -->
                <Tooltip :text="saveTooltip" placement="bottom">
                    <span
                        class="hidden md:inline-flex items-center gap-1.5 shrink-0 text-xs tabular-nums transition-colors"
                        :class="isDirty || isSaving ? 'text-ink-gray-5' : 'text-ink-gray-4'"
                        aria-live="polite"
                    >
                        <span
                            class="size-1.5 rounded-full transition-colors"
                            :class="isSaving ? 'bg-gray-400 animate-pulse' : isDirty ? 'bg-amber-500' : 'bg-green-600'"
                            aria-hidden="true"
                        />
                        {{ saveStatus }}
                    </span>
                </Tooltip>

                <!-- Publish: shown only when pressing it would change something -->
                <Tooltip v-if="needsPublish" :text="publishTooltip" placement="bottom">
                    <Button
                        variant="solid"
                        theme="gray"
                        size="sm"
                        :loading="isPublishing"
                        :label="publishLabel"
                        @click="onPublish"
                    />
                </Tooltip>
                <span
                    v-else
                    class="inline-flex items-center gap-1.5 shrink-0 rounded bg-surface-green-2 px-2 py-1 text-xs font-medium text-ink-green-3"
                >
                    <span class="size-1.5 rounded-full bg-green-600" aria-hidden="true" />
                    Published
                </span>
            </div>
        </div>
    </header>
    <PreviewDialog :show="showPreview" @close="showPreview = false" />
</template>

