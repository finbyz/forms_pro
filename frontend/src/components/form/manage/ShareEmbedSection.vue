<script setup lang="ts">
import { computed, ref } from "vue";
import { Button, FormControl, Tooltip } from "frappe-ui";
import { useManageForm } from "@/stores/form/manageForm";
import { useClipboard } from "@vueuse/core";
import { toast } from "vue-sonner";

const manageFormStore = useManageForm();
const { copy: copyUrl, copied: copiedUrl } = useClipboard({ copiedDuring: 2000 });
const { copy: copyEmbed, copied: copiedEmbed } = useClipboard({ copiedDuring: 2000 });

const formData = computed(() => manageFormStore.formData);
const isPublished = computed(() => manageFormStore.isPublished);

const embedHeight = ref("650");
const embedWidth = ref("100%");
const embedBorder = ref(true);

const fullPublicUrl = computed(() => {
    const route = formData.value?.route;
    if (!route) return "";
    return `${window.location.origin}/forms/p/${route}`;
});

/**
 * The embed snippet.
 *
 * Two things were wrong with the plain <iframe> this used to emit. Its inline
 * style hard-coded `width: 100%`, which overrides the width attribute, so the
 * Width control did nothing. And a bare iframe cannot talk to the host page, so
 * the `formspro_form_submit` dataLayer event Google Tag Manager needs was never
 * pushed -- there was nothing to push it.
 *
 * The loader script fixes both: it applies the chosen size, and it forwards the
 * submission to the host as a dataLayer event and a `forms-pro-submitted`
 * DOM event. Leaving Height blank lets the form grow to fit its content.
 */
const embedCode = computed(() => {
    const route = formData.value?.route;
    if (!route) return "<!-- Form URL not available -->";

    const origin = window.location.origin;
    const src = `${origin}/api/method/forms_pro.api.v1.public.get_embed_script`;
    const height = embedHeight.value?.trim();
    const width = embedWidth.value?.trim() || "100%";
    const borderStyle = embedBorder.value
        ? ' style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;"'
        : "";

    return [
        `<div data-forms-pro="${route}"${borderStyle}></div>`,
        `<script`,
        `  src="${src}"`,
        `  data-route="${route}"`,
        `  data-base="${origin}"`,
        `  data-width="${withUnit(width)}"`,
        height ? `  data-height="${withUnit(height)}"` : "  <!-- height omitted: grows to fit -->",
        `><\/script>`,
    ].join("\n");
});

/** "650" means pixels; "100%" or "40rem" are already sized. */
function withUnit(value: string): string {
    return /^\d+$/.test(value) ? `${value}px` : value;
}

const qrCodeUrl = computed(() => {
    if (!fullPublicUrl.value) return "";
    return `https://api.qrserver.com/v1/create-qr-code/?size=260x260&margin=10&data=${encodeURIComponent(
        fullPublicUrl.value
    )}`;
});

function handleCopyUrl() {
    if (fullPublicUrl.value) {
        copyUrl(fullPublicUrl.value);
        toast.success("Form link copied to clipboard");
    }
}

function handleCopyEmbed() {
    if (embedCode.value) {
        copyEmbed(embedCode.value);
        toast.success("Embed HTML code copied to clipboard");
    }
}
</script>

<template>
    <div class="flex flex-col gap-6">
        <!-- Direct Link Sharing Section -->
        <div class="bg-surface-base border border-outline-gray-1 rounded-8 p-5 flex flex-col gap-4">
            <div>
                <h3 class="text-base font-semibold text-ink-gray-9">Direct Share Link</h3>
                <p class="text-xs text-ink-gray-5 mt-0.5">
                    Share this URL with respondents via email, messaging, or social media.
                </p>
            </div>

            <div class="flex items-center gap-2">
                <div class="flex-1 px-3 py-2 bg-surface-gray-1 border border-outline-gray-2 rounded-6 font-mono text-xs text-ink-gray-8 truncate select-all">
                    {{ fullPublicUrl || "Form route not configured" }}
                </div>
                <Button
                    variant="solid"
                    size="sm"
                    :disabled="!fullPublicUrl"
                    @click="handleCopyUrl"
                >
                    <template #prefix>
                        <lucide-check v-if="copiedUrl" class="size-3.5 mr-1" aria-hidden="true" />
                        <lucide-copy v-else class="size-3.5 mr-1" aria-hidden="true" />
                    </template>
                    {{ copiedUrl ? "Copied!" : "Copy Link" }}
                </Button>
                <a
                    v-if="fullPublicUrl"
                    :href="fullPublicUrl"
                    target="_blank"
                >
                    <Button variant="outline" size="sm">
                        <template #prefix>
                            <lucide-external-link class="size-3.5 mr-1" aria-hidden="true" />
                        </template>
                        Open
                    </Button>
                </a>
            </div>

            <div v-if="!isPublished" class="p-3 bg-amber-50 border border-amber-200 rounded-6 text-xs text-amber-800 flex items-center gap-2">
                <lucide-alert-triangle class="size-4 shrink-0 text-amber-600" aria-hidden="true" />
                <span>This form is currently unpublished. External visitors will not be able to view or submit it until you publish it.</span>
            </div>
        </div>

        <!-- Iframe Embed Generator -->
        <div class="bg-surface-base border border-outline-gray-1 rounded-8 p-5 flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <div>
                    <h3 class="text-base font-semibold text-ink-gray-9">Embed in Website</h3>
                    <p class="text-xs text-ink-gray-5 mt-0.5">
                        Copy this snippet to embed this form into your website, WordPress, Shopify, or custom HTML.
                    </p>
                </div>
                <Button
                    variant="solid"
                    size="sm"
                    :disabled="!fullPublicUrl"
                    @click="handleCopyEmbed"
                >
                    <template #prefix>
                        <lucide-check v-if="copiedEmbed" class="size-3.5 mr-1" aria-hidden="true" />
                        <lucide-copy v-else class="size-3.5 mr-1" aria-hidden="true" />
                    </template>
                    {{ copiedEmbed ? "Copied Snippet!" : "Copy Embed Code" }}
                </Button>
            </div>

            <!-- Embed Options -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-surface-gray-1 rounded-6 text-xs">
                <div>
                    <label class="block text-ink-gray-6 font-medium mb-1">Height (px)</label>
                    <FormControl
                        type="text"
                        size="sm"
                        v-model="embedHeight"
                        placeholder="650"
                    />
                </div>
                <div>
                    <label class="block text-ink-gray-6 font-medium mb-1">Width</label>
                    <FormControl
                        type="text"
                        size="sm"
                        v-model="embedWidth"
                        placeholder="100%"
                    />
                </div>
                <div class="flex flex-col justify-end">
                    <label class="flex items-center gap-2 cursor-pointer text-ink-gray-7 py-2">
                        <input
                            type="checkbox"
                            v-model="embedBorder"
                            class="rounded border-outline-gray-2 text-ink-blue-6 focus:ring-ink-blue-5"
                        />
                        <span>Include subtle card border</span>
                    </label>
                </div>
            </div>

            <!-- Code block display -->
            <div class="relative">
                <pre class="p-3.5 bg-surface-gray-2 border border-outline-gray-2 rounded-6 font-mono text-xs text-ink-gray-9 overflow-x-auto whitespace-pre"><code>{{ embedCode }}</code></pre>
            </div>
        </div>

        <!-- QR Code Sharing -->
        <div class="bg-surface-base border border-outline-gray-1 rounded-8 p-5 flex flex-col sm:flex-row items-center justify-between gap-6">
            <div class="flex flex-col gap-2">
                <h3 class="text-base font-semibold text-ink-gray-9">QR Code</h3>
                <p class="text-xs text-ink-gray-5 max-w-md">
                    Print this QR code on flyers, signs, or brochures. When scanned with a smartphone camera, respondents are directed straight to your form.
                </p>
                <div class="flex items-center gap-2 mt-2">
                    <a
                        :href="qrCodeUrl"
                        download="form-qr-code.png"
                        target="_blank"
                    >
                        <Button variant="outline" size="sm">
                            <template #prefix>
                                <lucide-download class="size-3.5 mr-1" aria-hidden="true" />
                            </template>
                            Download QR Image
                        </Button>
                    </a>
                </div>
            </div>

            <div class="p-3 bg-surface-white border border-outline-gray-2 rounded-xl shadow-sm shrink-0">
                <img
                    :src="qrCodeUrl"
                    alt="Form QR Code"
                    class="size-36 object-contain"
                    loading="lazy"
                />
            </div>
        </div>
    </div>
</template>
