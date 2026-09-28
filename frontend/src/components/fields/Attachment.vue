<script setup lang="ts">
import { ErrorMessage, FileUploader } from "frappe-ui";
import { computed, ref } from "vue";

defineProps({
    field: {
        type: Object,
        required: true,
    },
});

const value = defineModel<string>();

/**
 * Whether a file is attached is read from the model, never from local state.
 *
 * Moving between steps unmounts this component -- FormRenderer only renders the
 * current step -- so anything held in a local ref is gone on the way back. The
 * uploaded URL survives in the form data, but the preview used to be gated on a
 * local flag, so returning to the step showed an empty Upload button and people
 * re-uploaded a file that was already attached.
 */
const hasFile = computed(() => !!value.value);

export type FileType = {
    content_hash: string;
    creation: string;
    docstatus: number;
    doctype: string;
    file_name: string;
    file_size: number;
    file_type: string;
    file_url: string;
    folder: string;
    idx: number;
    is_attachments_folder: number;
    is_folder: number;
    is_home_folder: number;
    is_private: number;
    modified: string;
    modified_by: string;
    name: string;
    owner: string;
    uploaded_to_dropbox: number;
    uploaded_to_google_drive: number;
};

const fileData = ref<FileType | null>(null);

const formatFileSize = (fileSize: number) => {
    if (fileSize < 1024) return `${fileSize} B`;
    if (fileSize < 1024 * 1024) return `${(fileSize / 1024).toFixed(2)} KB`;
    if (fileSize < 1024 * 1024 * 1024) return `${(fileSize / 1024 / 1024).toFixed(2)} MB`;
    return `${(fileSize / 1024 / 1024 / 1024).toFixed(2)} GB`;
};

const handleChange = (file: FileType) => {
    fileData.value = file;
    if (file.file_url) {
        value.value = file.file_url;
    }
};

/**
 * After a remount only the URL is left, so fall back to the name inside it.
 * The size is not recoverable and is simply not shown.
 */
const displayName = computed(() => {
    if (fileData.value?.file_name) return fileData.value.file_name;
    const url = value.value ?? "";
    try {
        return decodeURIComponent(url.split("/").pop() || url);
    } catch {
        return url.split("/").pop() || url;
    }
});

const displaySize = computed(() => fileData.value?.file_size ?? null);

// Guests can only upload when System Settings allows it, and the allowlist
// there is keyed on this doctype — so tag the upload rather than leaving guest
// uploads open site-wide.
const uploadArgs = {
    doctype: "FP Form Submission",
    private: true,
    folder: "Home/Attachments",
};

const handleRemove = () => {
    fileData.value = null;
    value.value = "";
};
</script>
<template>
    <div class="flex gap-2 flex-col mt-2">
        <FileUploader
            v-if="!hasFile"
            :upload-args="uploadArgs"
            @success="(file: FileType) => handleChange(file)"
        >
            <!-- @vue-ignore -->
            <template #default="{ uploading, progress, error, openFileSelector }">
                <Button @click="openFileSelector()" :loading="uploading">
                    {{ uploading ? `Uploading ${progress}%` : "Upload" }}
                </Button>
                <ErrorMessage :message="error" />
            </template>
        </FileUploader>
        <div v-if="hasFile" class="p-4 bg-white border rounded-md flex flex-col gap-2">
            <a :href="value" target="_blank" class="text-sm font-medium">
                {{ displayName }}
            </a>
            <span v-if="displaySize !== null" class="text-sm text-gray-500">
                {{ formatFileSize(displaySize) }}
            </span>
            <Button
                theme="red"
                label="Remove"
                icon="trash"
                tooltip="Remove file"
                @click="handleRemove"
            />
        </div>
    </div>
</template>
