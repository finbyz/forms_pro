<script setup lang="ts">
import { createResource } from "frappe-ui";
import { useManageForm } from "@/stores/form/manageForm";
import { computed, watch } from "vue";
import { toast } from "vue-sonner";
import { formatDateTime } from "@/utils/date";
import { Fieldtype } from "@/types/formfield";
import SubmissionFieldValue from "@/components/form/submissions/SubmissionFieldValue.vue";

const props = defineProps<{
    submissionId: string;
    doctype: string;
}>();

const emit = defineEmits<{
    (e: "loaded", data: any): void;
}>();

const manageFormStore = useManageForm();

const submissionResource = createResource({
    url: "forms_pro.api.submission.get_submission_response",
    makeParams() {
        return {
            submission_id: props.submissionId,
            doctype: props.doctype,
        };
    },
    onError(error: Error) {
        toast.error("Failed to fetch submission details", {
            description: error.message,
        });
    },
});

const submissionData = computed(() => submissionResource.data ?? null);

watch(
    () => props.submissionId,
    (newId) => {
        if (newId) {
            submissionResource.fetch();
        }
    },
    { immediate: true }
);

watch(
    submissionData,
    (data) => {
        if (data) {
            emit("loaded", data);
        }
    },
    { immediate: true }
);

const deskInfo = computed(() => {
    const targetDocType = submissionData.value?.target_doctype || props.doctype;
    const targetName = submissionData.value?.target_name;
    if (targetDocType && targetName) {
        const slug = targetDocType.toLowerCase().replace(/\s+/g, "-");
        return {
            label: `${targetDocType}: ${targetName}`,
            url: `/app/${slug}/${encodeURIComponent(targetName)}`,
        };
    }
    if (targetDocType && submissionData.value?.name) {
        const slug = targetDocType.toLowerCase().replace(/\s+/g, "-");
        return {
            label: `${targetDocType}: ${submissionData.value.name}`,
            url: `/app/${slug}/${encodeURIComponent(submissionData.value.name)}`,
        };
    }
    if (submissionData.value?.name) {
        return {
            label: `Submission: ${submissionData.value.name}`,
            url: `/app/fp-form-submission/${encodeURIComponent(submissionData.value.name)}`,
        };
    }
    return null;
});

const gridItems = computed(() => [
    {
        label: "Submission ID",
        key: "name",
        value: submissionData.value?.name,
        class: "font-mono",
    },
    {
        label: "Submitted On",
        key: "creation",
        value: formatDateTime(submissionData.value?.creation),
    },
    {
        label: "Last Modified",
        key: "modified",
        value: formatDateTime(submissionData.value?.modified),
    },
    {
        label: "Submitted By",
        key: "owner",
        value: submissionData.value?.owner,
    },
]);

const formFields = computed(() => {
    const fields = [...(manageFormStore.formFields || [])];
    const existingKeys = new Set(fields.map((f: any) => f.fieldname));
    if (submissionData.value) {
        const internalKeys = new Set([
            "name",
            "creation",
            "modified",
            "owner",
            "status",
            "target_doctype",
            "target_name",
            "fp_submission_status",
            "docstatus",
            "doctype",
        ]);
        for (const [key, val] of Object.entries(submissionData.value)) {
            if (!internalKeys.has(key) && !existingKeys.has(key)) {
                const isTable = Array.isArray(val) && val.length > 0 && typeof val[0] === "object";
                fields.push({
                    name: key,
                    fieldname: key,
                    label: key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
                    fieldtype: isTable ? Fieldtype.TABLE : Fieldtype.DATA,
                    options: "",
                } as any);
            }
        }
    }
    return fields;
});
</script>

<template>
    <div v-if="submissionResource.loading" class="text-sm text-ink-gray-5 py-4">Loading...</div>
    <div v-else-if="submissionData" class="flex flex-col gap-4">
        <div class="flex flex-col gap-4">
            <div class="grid grid-cols-3 gap-3 text-sm py-2">
                <template v-for="item in gridItems" :key="item.key">
                    <span class="text-ink-gray-5">{{ item.label }}</span>
                    <span class="text-ink-gray-8 col-span-2" :class="item.class">{{
                        item.value
                    }}</span>
                </template>
                <template v-if="deskInfo">
                    <span class="text-ink-gray-5">Desk View</span>
                    <span class="col-span-2">
                        <a
                            :href="deskInfo.url"
                            target="_blank"
                            class="inline-flex items-center gap-1.5 text-ink-blue-6 hover:text-ink-blue-7 hover:underline font-medium"
                        >
                            {{ deskInfo.label }}
                            <lucide-external-link class="w-3.5 h-3.5" aria-hidden="true" />
                        </a>
                    </span>
                </template>
            </div>
            <hr class="border-outline-gray-2" />
            <div class="flex flex-col gap-5 my-2">
                <SubmissionFieldValue
                    v-for="field in formFields"
                    :key="field.name"
                    :fieldname="field.fieldname"
                    :label="field.label"
                    :description="field.description"
                    :fieldtype="field.fieldtype"
                    :options="field.options"
                    :value="submissionData[field.fieldname]"
                />
            </div>
        </div>
    </div>
</template>
