<script setup lang="ts">
import { ref } from "vue";
import { Button } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import { useRouter } from "vue-router";
import { Copy, Archive } from "@lucide/vue";

const editFormStore = useEditForm();
const router = useRouter();
const duplicating = ref(false);
const archiving = ref(false);

async function duplicateForm() {
    const name = editFormStore.originalFormData?.name;
    if (!name) return;
    duplicating.value = true;
    try {
        const res = await (window as any).frappe.call({
            method: "forms_pro.api.v1.builder.data.duplicate_form",
            type: "POST",
            args: { form_name: name },
        });
        const newName = res.message?.name;
        const newTitle = res.message?.title;
        if (newName) {
            (window as any).frappe.show_alert({ message: `"${newTitle}" created.`, indicator: "green" });
            router.push({ name: "Edit Form", params: { id: newName } });
        }
    } catch {
        (window as any).frappe.show_alert({ message: "Duplication failed.", indicator: "red" });
    } finally {
        duplicating.value = false;
    }
}

async function archiveForm() {
    const name = editFormStore.originalFormData?.name;
    if (!name || !confirm("Archive this form? It will be hidden from public routes.")) return;
    archiving.value = true;
    try {
        await (window as any).frappe.call({
            method: "forms_pro.api.v1.builder.data.archive_form",
            type: "POST",
            args: { form_name: name },
        });
        (window as any).frappe.show_alert({ message: "Form archived.", indicator: "orange" });
        router.push({ name: "Home" });
    } catch {
        (window as any).frappe.show_alert({ message: "Archive failed.", indicator: "red" });
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
