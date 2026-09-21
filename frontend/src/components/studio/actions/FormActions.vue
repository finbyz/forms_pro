<script setup lang="ts">
import { ref } from "vue";
import { Button, createResource } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import { useRouter } from "vue-router";
import { toast } from "vue-sonner";

const editFormStore = useEditForm();
const router = useRouter();
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
            }
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
            }
        }).submit();
        toast.warning("Form archived.");
        router.push({ name: "Home" });
    } catch {
        toast.error("Archive failed.");
    } finally {
        archiving.value = false;
    }
}
</script>

<template>
    <div class="flex flex-col gap-1 py-1">
        <Button label="Duplicate" variant="ghost" :loading="duplicating" icon-left="copy" @click="duplicateForm" />
        <Button label="Archive" variant="ghost" theme="red" :loading="archiving" icon-left="archive" @click="archiveForm" />
    </div>
</template>
