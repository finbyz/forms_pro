<script setup lang="ts">
import { computed, ref } from "vue";
import { Button, Tooltip, Dialog } from "frappe-ui";
import { useManageForm } from "@/stores/form/manageForm";
import { useClipboard } from "@vueuse/core";
import { toast } from "vue-sonner";

const emit = defineEmits<{ (e: "open-share-tab"): void }>();

const manageFormStore = useManageForm();
const { copy, copied } = useClipboard({ copiedDuring: 2000 });
const showQrModal = ref(false);

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

const qrCodeUrl = computed(() => {
    if (!fullPublicUrl.value) return "";
    return `https://api.qrserver.com/v1/create-qr-code/?size=260x260&margin=10&data=${encodeURIComponent(
        fullPublicUrl.value
    )}`;
});

function copyLink() {
    if (fullPublicUrl.value) {
        copy(fullPublicUrl.value);
        toast.success("Public form link copied to clipboard");
    }
}

function openForm() {
    if (fullPublicUrl.value) {
        window.open(fullPublicUrl.value, "_blank");
    }
}
</script>

<template>
    <div
        class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3.5 bg-surface-gray-1 border border-outline-gray-1 rounded-8"
    >
        <!-- Left: URL Info -->
        <div class="flex items-center gap-3 min-w-0 flex-1">
            <div class="p-2 rounded-6 bg-surface-base border border-outline-gray-1 text-ink-gray-6 shrink-0">
                <lucide-link-2 class="size-4 text-ink-gray-7" aria-hidden="true" />
            </div>
            <div class="flex flex-col min-w-0 flex-1">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-medium text-ink-gray-5">Form Link</span>
                    <span
                        v-if="formData?.login_required"
                        class="text-[10px] font-medium px-1.5 py-0.2 rounded bg-surface-gray-2 text-ink-gray-6 border border-outline-gray-1"
                    >
                        Requires Login
                    </span>
                    <span
                        v-else
                        class="text-[10px] font-medium px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200"
                    >
                        Public Access
                    </span>
                </div>
                <div class="flex items-center gap-1.5 mt-0.5">
                    <span class="text-xs font-mono text-ink-gray-8 truncate select-all">
                        {{ fullPublicUrl || "No route set for this form" }}
                    </span>
                </div>
            </div>
        </div>

        <!-- Right: Actions -->
        <div class="flex items-center gap-2 shrink-0">
            <!-- Copy Link Button -->
            <Button
                variant="outline"
                size="sm"
                :disabled="!fullPublicUrl"
                @click="copyLink"
            >
                <template #prefix>
                    <lucide-check v-if="copied" class="size-3.5 mr-1 text-green-600" aria-hidden="true" />
                    <lucide-copy v-else class="size-3.5 mr-1 text-ink-gray-6" aria-hidden="true" />
                </template>
                {{ copied ? "Copied!" : "Copy Link" }}
            </Button>

            <!-- Open Form Button -->
            <Tooltip :text="isPublished ? 'Open in new tab' : 'Form is not published yet'" placement="bottom">
                <Button
                    variant="outline"
                    size="sm"
                    :disabled="!isPublished || !fullPublicUrl"
                    @click="openForm"
                >
                    <template #prefix>
                        <lucide-external-link class="size-3.5 mr-1 text-ink-gray-6" aria-hidden="true" />
                    </template>
                    Open
                </Button>
            </Tooltip>

            <!-- QR Code Button -->
            <Tooltip text="View QR code for mobile scanning" placement="bottom">
                <Button
                    variant="outline"
                    size="sm"
                    :disabled="!fullPublicUrl"
                    @click="showQrModal = true"
                >
                    <template #prefix>
                        <lucide-qr-code class="size-3.5 mr-1 text-ink-gray-6" aria-hidden="true" />
                    </template>
                    QR Code
                </Button>
            </Tooltip>

            <!-- Share & Embed Tab Shortcut -->
            <Button
                variant="ghost"
                size="sm"
                @click="emit('open-share-tab')"
            >
                <template #prefix>
                    <lucide-code class="size-3.5 mr-1 text-ink-gray-6" aria-hidden="true" />
                </template>
                Embed
            </Button>
        </div>

        <!-- QR Code Modal -->
        <Dialog
            v-model="showQrModal"
            :options="{
                title: 'Form QR Code',
                size: 'sm',
            }"
        >
            <template #body-content>
                <div class="flex flex-col items-center gap-4 py-3">
                    <p class="text-xs text-ink-gray-5 text-center">
                        Scan with any smartphone camera to open and test this form instantly.
                    </p>
                    <div class="p-3 bg-surface-white rounded-xl border border-outline-gray-2 shadow-sm">
                        <img
                            :src="qrCodeUrl"
                            alt="Form QR Code"
                            class="size-52 object-contain"
                            loading="lazy"
                        />
                    </div>
                    <span class="text-xs font-mono text-ink-gray-6 truncate max-w-full text-center px-4">
                        {{ fullPublicUrl }}
                    </span>
                    <div class="flex gap-2 w-full mt-2">
                        <Button
                            variant="outline"
                            class="flex-1"
                            size="sm"
                            @click="copyLink"
                        >
                            <template #prefix>
                                <lucide-copy class="size-3.5 mr-1" aria-hidden="true" />
                            </template>
                            Copy Link
                        </Button>
                        <a
                            :href="qrCodeUrl"
                            download="form-qr-code.png"
                            target="_blank"
                            class="flex-1"
                        >
                            <Button variant="solid" class="w-full" size="sm">
                                <template #prefix>
                                    <lucide-download class="size-3.5 mr-1" aria-hidden="true" />
                                </template>
                                Download QR
                            </Button>
                        </a>
                    </div>
                </div>
            </template>
        </Dialog>
    </div>
</template>
