<script setup lang="ts">
import { computed } from "vue";
import { Badge, Button, Dropdown, Tooltip } from "frappe-ui";
import { useManageForm } from "@/stores/form/manageForm";
import Avatar from "@/components/ui/Avatar.vue";
import { formatPrettyDate } from "@/utils/date";
import { useClipboard } from "@vueuse/core";
import { toast } from "vue-sonner";
import { useRouter } from "vue-router";

const manageFormStore = useManageForm();
const router = useRouter();
const { copy } = useClipboard();

const formData = computed(() => manageFormStore.formData);
const isPublished = computed(() => manageFormStore.isPublished);

const publicPath = computed(() => {
    const route = formData.value?.route;
    return route ? `/forms/p/${route}` : "";
});

const fullPublicUrl = computed(() => {
    if (!publicPath.value) return "";
    return `${window.location.origin}${publicPath.value}`;
});

const deskDocTypeUrl = computed(() => {
    const dt = formData.value?.target_doctype;
    if (!dt) return "";
    const slug = dt.toLowerCase().replace(/\s+/g, "-");
    return `/app/${slug}`;
});

const deskFormUrl = computed(() => {
    const name = formData.value?.name;
    if (!name) return "";
    return `/app/form/${encodeURIComponent(name)}`;
});

function openLiveForm() {
    if (publicPath.value) {
        window.open(fullPublicUrl.value, "_blank");
    }
}

function copyUrl() {
    if (fullPublicUrl.value) {
        copy(fullPublicUrl.value);
        toast.success("Form link copied to clipboard");
    }
}

const dropdownItems = computed(() => [
    {
        label: "Copy Public URL",
        icon: "copy",
        onClick: copyUrl,
    },
    {
        label: `View DocType (${formData.value?.target_doctype || "Desk"})`,
        icon: "external-link",
        onClick: () => {
            if (deskDocTypeUrl.value) window.open(deskDocTypeUrl.value, "_blank");
        },
    },
    {
        label: "Open Form in Desk",
        icon: "file-text",
        onClick: () => {
            if (deskFormUrl.value) window.open(deskFormUrl.value, "_blank");
        },
    },
]);
</script>

<template>
    <div class="flex flex-col gap-3 pb-2 border-b border-outline-gray-1">
        <!-- Top Status & Actions Header -->
        <div class="flex flex-wrap items-center justify-between gap-4">
            <!-- Left: Status Badge & Form Title -->
            <div class="flex items-center gap-3 min-w-0">
                <div class="p-2.5 rounded-lg bg-surface-gray-2 text-ink-gray-7 shrink-0">
                    <lucide-file-text class="w-6 h-6 text-ink-gray-8" aria-hidden="true" />
                </div>
                <div class="flex flex-col min-w-0">
                    <div class="flex items-center gap-2.5">
                        <h1 class="text-2xl font-bold text-ink-gray-9 truncate tracking-tight">
                            {{ formData?.title || "Untitled Form" }}
                        </h1>

                        <!-- Live Status Pill -->
                        <span
                            v-if="isPublished"
                            class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20"
                        >
                            <span class="size-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            Published
                        </span>
                        <span
                            v-else
                            class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-gray-2 text-ink-gray-6 ring-1 ring-outline-gray-2"
                        >
                            <span class="size-1.5 rounded-full bg-ink-gray-4"></span>
                            Draft / Offline
                        </span>
                    </div>

                    <!-- Subtitle Metadata: Created by, dates, target doctype -->
                    <div class="flex items-center gap-2 text-xs text-ink-gray-5 mt-1 flex-wrap">
                        <span v-if="formData?.creation">
                            Created {{ formatPrettyDate(formData?.creation) }}
                        </span>
                        <template v-if="formData?.owner">
                            <span>by</span>
                            <div class="inline-flex items-center gap-1">
                                <Avatar :userId="formData.owner" size="xs" />
                                <span class="font-medium text-ink-gray-7">{{ formData.owner }}</span>
                            </div>
                        </template>
                        <template v-if="formData?.modified">
                            <span>•</span>
                            <span>Modified {{ formatPrettyDate(formData?.modified) }}</span>
                        </template>
                        <template v-if="formData?.target_doctype">
                            <span>•</span>
                            <a
                                :href="deskDocTypeUrl"
                                target="_blank"
                                class="inline-flex items-center gap-1 text-ink-blue-6 hover:text-ink-blue-7 hover:underline"
                            >
                                <lucide-database class="size-3" aria-hidden="true" />
                                <span>DocType: {{ formData.target_doctype }}</span>
                                <lucide-external-link class="size-2.5" aria-hidden="true" />
                            </a>
                        </template>
                    </div>
                </div>
            </div>

            <!-- Right: Action Buttons -->
            <div class="flex items-center gap-2 shrink-0">
                <!-- Open Live Form Button -->
                <Tooltip :text="isPublished ? 'Open live form in new tab' : 'Form must be published first'" placement="bottom">
                    <Button
                        variant="outline"
                        size="md"
                        :disabled="!isPublished || !publicPath"
                        @click="openLiveForm"
                    >
                        <template #prefix>
                            <lucide-external-link class="size-4 mr-1 text-ink-gray-6" aria-hidden="true" />
                        </template>
                        View Live
                    </Button>
                </Tooltip>

                <!-- Publish / Unpublish Toggle Button -->
                <Tooltip :text="isPublished ? 'Take form offline' : 'Make form publicly accessible'" placement="bottom">
                    <Button
                        :variant="isPublished ? 'subtle' : 'solid'"
                        :theme="isPublished ? 'red' : 'gray'"
                        size="md"
                        :loading="manageFormStore.isTogglingPublish"
                        @click="manageFormStore.togglePublish"
                    >
                        <template #prefix>
                            <lucide-globe class="size-4 mr-1" aria-hidden="true" />
                        </template>
                        {{ isPublished ? "Unpublish" : "Publish" }}
                    </Button>
                </Tooltip>

                <!-- Edit in Studio Button -->
                <Button
                    variant="solid"
                    size="md"
                    @click="
                        router.push({
                            name: 'Edit Form',
                            params: { id: formData?.name },
                        })
                    "
                >
                    <template #prefix>
                        <lucide-edit-3 class="size-4 mr-1" aria-hidden="true" />
                    </template>
                    Edit Form
                </Button>

                <!-- More Options Dropdown -->
                <Dropdown
                    :button="{
                        icon: 'more-horizontal',
                        variant: 'ghost',
                    }"
                    :options="dropdownItems"
                />
            </div>
        </div>
    </div>
</template>
