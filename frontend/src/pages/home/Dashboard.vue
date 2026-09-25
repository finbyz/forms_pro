<template>
    <Dialog
        v-model="showNameDialog"
        :options="{ title: 'Name your form' }"
    >
        <template #body-content>
            <div class="flex flex-col gap-2">
                <FormControl
                    v-model="newFormName"
                    type="text"
                    label="Form name"
                    placeholder="e.g. Solar Enquiry Form"
                    :disabled="creating"
                    @blur="verifyName"
                    @keyup.enter="confirmCreateForm"
                />
                <p class="text-xs text-ink-gray-5">
                    This is also used as the DocType name, so it must be unique.
                </p>
                <p v-if="nameError" class="text-xs text-ink-red-4">{{ nameError }}</p>
            </div>
        </template>
        <template #actions>
            <Button
                class="w-full"
                variant="solid"
                :loading="creating || checkingName"
                :disabled="!newFormName.trim() || creating"
                @click="confirmCreateForm"
            >Create</Button>
        </template>
    </Dialog>
    <Dialog
        v-model="showSelectDoctypeDialog"
        :options="{
            title: 'Select DocType',
        }"
    >
        <template #body-content>
            <div class="flex flex-col gap-2">
                <label class="text-sm font-medium">DocType</label>
                <Combobox
                    v-model="selectedDoctype"
                    :options="doctypesOptions"
                    placeholder="Search or select DocType..."
                    :open-on-click="true"
                    :open-on-focus="true"
                />
            </div>
        </template>
        <template #actions>
            <Button
                class="w-full"
                variant="solid"
                :loading="creatingWithDoctype"
                :disabled="!selectedDoctype || creatingWithDoctype"
                @click="handleCreateDraftFormWithDoctype"
            >Create</Button>
        </template>
    </Dialog>
    <div class="flex flex-col gap-4 w-full overflow-y-auto">
        <Breadcrumbs :items="breadcrumbItems" />
        <div class="flex flex-col gap-2">
            <h2 class="text-3xl font-bold">Dashboard</h2>
            <p class="text-base">Manage and create forms</p>
        </div>
        <template v-if="user.user?.has_desk_access">
            <Dropdown
                class="w-fit"
                :button="{
                    label: 'Create',
                    iconLeft: 'plus',
                    variant: 'solid',
                }"
                :options="[
                    {
                        label: 'Create New',
                        onClick: handleCreateDraftForm,
                    },
                    {
                        label: 'Create from Existing DocType',
                        onClick: handleOpenSelectDoctypeDialog,
                    },
                ]"
            />
        </template>
        <template v-else>
            <Button class="w-fit" variant="solid" iconLeft="plus" @click="handleCreateDraftForm">
                Create New
            </Button>
        </template>
        <div class="flex flex-col gap-2">
            <h3 class="font-medium">Recent</h3>
            <p class="text-sm" v-if="teamForms.loading">Loading...</p>
            <p class="text-sm" v-else-if="!teamForms.data || teamForms.data.length === 0">
                No forms created yet
            </p>
            <div
                class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
                v-else
            >
                <div v-for="form in teamForms.data" :key="form.name">
                    <FormPreviewCard :form="form" />
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { ref, watch, computed } from "vue";
import { toast } from "vue-sonner";
import { useUser } from "@/stores/user";
import {
    Dropdown,
    Dialog,
    createResource,
    Combobox,
    Breadcrumbs,
    FormControl,
} from "frappe-ui";
import {
    createNewFormWithDoctype,
    createNewForm,
    checkFormNameAvailable,
} from "@/utils/form_generator";
import FormPreviewCard from "@/components/dashboard/FormPreviewCard.vue";
const router = useRouter();
const showSelectDoctypeDialog = ref(false);
const selectedDoctype = ref<string | null>(null);
const showNameDialog = ref(false);
const newFormName = ref("");
const nameError = ref("");
const checkingName = ref(false);
const creating = ref(false);
const creatingWithDoctype = ref(false);
const user = useUser();

const breadcrumbItems = ref([{ label: "Manage" }, { label: "All Forms" }]);

const doctypesList = createResource({
    url: "forms_pro.api.form.get_doctype_list",
});

// Ensure doctypesList.data is always an array to prevent Combobox errors
const doctypesOptions = computed(() => doctypesList.data || []);

const handleCreateDraftFormWithDoctype = async () => {
    if (!selectedDoctype.value || !user.currentTeam?.name) {
        toast.error("Error occurred while creating form. Check DocType Selected.");
        return;
    }
    creatingWithDoctype.value = true;
    try {
        const data = await createNewFormWithDoctype(selectedDoctype.value, user.currentTeam.name);
        showSelectDoctypeDialog.value = false;
        const formDoc = data.form_document;
        selectedDoctype.value = null;
        router.push({
            name: "Edit Form",
            params: {
                id: formDoc,
            },
        });
    } catch (e: any) {
        toast.error(e?.message ?? "Error occurred while creating form.");
    } finally {
        creatingWithDoctype.value = false;
    }
};

const handleOpenSelectDoctypeDialog = () => {
    selectedDoctype.value = null;
    if (!doctypesList.data?.length) {
        doctypesList.fetch();
    }
    showSelectDoctypeDialog.value = true;
};

const handleCreateDraftForm = () => {
    if (!user.currentTeam?.name) {
        toast.error("Error occured while creating form. User has no default team.");
        return;
    }
    newFormName.value = "";
    nameError.value = "";
    showNameDialog.value = true;
};

// The name becomes the DocType name, so check before creating rather than
// letting the insert fail.
const verifyName = async () => {
    const name = newFormName.value.trim();
    nameError.value = "";
    if (!name) return false;
    checkingName.value = true;
    try {
        const res = await checkFormNameAvailable(name);
        if (!res.available) {
            nameError.value = `"${res.name}" already exists. Please choose another name.`;
            return false;
        }
        return true;
    } catch (e: any) {
        nameError.value = e?.message ?? "Could not verify the name.";
        return false;
    } finally {
        checkingName.value = false;
    }
};

const confirmCreateForm = async () => {
    if (!user.currentTeam?.name) return;
    const name = newFormName.value.trim();
    if (!name) {
        nameError.value = "Please enter a form name.";
        return;
    }
    if (!(await verifyName())) return;

    creating.value = true;
    try {
        const data = await createNewForm(user.currentTeam.name, name);
        showNameDialog.value = false;
        router.push({ name: "Edit Form", params: { id: data.form_document } });
    } catch (e: any) {
        nameError.value = e?.message ?? "Could not create the form.";
    } finally {
        creating.value = false;
    }
};

const teamForms = createResource({
    url: "forms_pro.api.team.get_team_forms",
    makeParams() {
        return {
            team_id: user.currentTeam?.name,
        };
    },
    loading: true,
    cache: "teamForms",
});

watch(
    () => user.currentTeam,
    (currentTeam) => {
        if (currentTeam) {
            teamForms.fetch();
        }
    },
    { immediate: true }
);

watch(
    () => user.user,
    (user) => {
        if (user && user.has_desk_access) {
            doctypesList.fetch();
        }
    },
    { immediate: true }
);

watch(showSelectDoctypeDialog, (open) => {
    if (!open) {
        selectedDoctype.value = null;
    }
});
</script>
