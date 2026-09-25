<script setup lang="ts">
import { useManageForm } from "@/stores/form/manageForm";
import { useTeam } from "@/stores/team";
import { useUser } from "@/stores/user";
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { Button, Checkbox, ListView, Badge } from "frappe-ui";
import { UsersRound } from "@lucide/vue";
import Avatar from "@/components/ui/Avatar.vue";
import type { PermissionTypes } from "@/stores/form/manageForm";
import ShareAccessModal from "./ShareAccessModal.vue";
import RemoveAccessModal from "./RemoveAccessModal.vue";
import InviteMemberDialog from "@/components/team/InviteMemberDialog.vue";

const router = useRouter();
const manageFormStore = useManageForm();
const teamStore = useTeam();
const userStore = useUser();

const openModal = ref(false);
const openRemoveAccessModal = ref(false);
const openAddMemberDialog = ref(false);
const selectedUserToRemove = ref<string | null>(null);

const formTeamId = computed(() => {
    return (
        manageFormStore.formData?.linked_team_id ||
        teamStore.targetTeamId ||
        userStore.currentTeam?.name ||
        ""
    );
});

const formTeamName = computed(() => {
    return (
        manageFormStore.formData?.linked_team_name ||
        userStore.currentTeam?.team_name ||
        "Team"
    );
});

watch(
    formTeamId,
    (id) => {
        if (id) {
            teamStore.initialize(id);
        }
    },
    { immediate: true }
);

function showRemoveAccessModal(email: string) {
    selectedUserToRemove.value = email;
    openRemoveAccessModal.value = true;
}

const columns = ref([
    {
        label: "Name",
        key: "full_name",
        width: 2,
    },
    {
        label: "",
        key: "comment",
    },
    {
        label: "Read",
        key: "read",
    },
    {
        label: "Write",
        key: "write",
    },
    {
        label: "Share",
        key: "share",
    },
    {
        label: "Actions",
        key: "actions",
    },
]);

function setPermission(row: any, column: any, value: boolean) {
    const userId = row.email;
    const permission = column.key as PermissionTypes;
    manageFormStore.setPermission(userId, permission, value);
}
</script>
<template>
    <ShareAccessModal v-model="openModal" />
    <RemoveAccessModal
        v-model="openRemoveAccessModal"
        v-model:selected-user-to-remove="selectedUserToRemove"
    />
    <InviteMemberDialog v-model="openAddMemberDialog" :team-id="formTeamId" />
    <div v-if="manageFormStore.formAccessResource.data" class="flex flex-col gap-5">
        <!-- Team Context Banner -->
        <div class="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-lg border border-outline-gray-2 bg-surface-gray-1">
            <div class="flex items-center gap-3 min-w-0">
                <div class="size-9 rounded-lg bg-surface-gray-3 flex items-center justify-center text-ink-gray-7 shrink-0">
                    <UsersRound class="size-5" />
                </div>
                <div class="min-w-0">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-semibold uppercase tracking-wider text-ink-gray-5">Assigned Team:</span>
                        <Badge theme="blue" size="sm" class="font-medium">{{ formTeamName }}</Badge>
                    </div>
                    <p class="text-xs text-ink-gray-5 mt-0.5">
                        Team members can be given view, edit, or share permissions on this form.
                    </p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    icon-left="users"
                    @click="router.push('/team')"
                >
                    Manage Team
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    icon-left="plus"
                    @click="openAddMemberDialog = true"
                >
                    Add to Team
                </Button>
            </div>
        </div>

        <div class="flex items-center justify-between">
            <div class="space-y-0.5">
                <p class="text-base font-medium text-ink-gray-8">Form Access & Permissions</p>
                <p class="text-sm text-ink-gray-5">
                    Manage which users can view, edit, or share this form.
                </p>
            </div>
            <div class="flex gap-2">
                <Button variant="solid" size="sm" icon-left="plus" @click="openModal = true">
                    Share Access
                </Button>
            </div>
        </div>
        <ListView
            :columns="columns"
            :rows="manageFormStore.formAccessResource.data"
            :options="{
                selectable: false,
            }"
            row-key="email"
        >
            <!-- @vue-ignore -->
            <template #cell="{ item, row, column }">
                <div
                    v-if="column.key === 'full_name'"
                    class="flex items-center gap-2 text-ink-gray-8 text-sm"
                >
                    <Avatar :userId="row.email" />
                    <p>{{ row.full_name }}</p>
                </div>
                <div v-else-if="column.key === 'comment'" class="flex">
                    <span
                        v-if="row.email === manageFormStore.formOwner"
                        class="text-ink-gray-5 text-sm italic"
                    >
                        Owner
                    </span>
                </div>
                <div v-else-if="column.key === 'actions'" class="flex">
                    <Button
                        size="sm"
                        theme="red"
                        icon="trash"
                        @click="showRemoveAccessModal(row.email)"
                        :disabled="row.email === manageFormStore.formOwner"
                        :tooltip="
                            row.email === manageFormStore.formOwner
                                ? 'Owner cannot be removed'
                                : 'Remove Access'
                        "
                    />
                </div>
                <div v-else class="flex">
                    <Checkbox
                        :disabled="
                            !manageFormStore.userHasShareAccess ||
                            row.email === manageFormStore.formOwner
                        "
                        :model-value="item"
                        @update:model-value="setPermission(row, column, $event)"
                    />
                </div>
            </template>
        </ListView>
    </div>
</template>
