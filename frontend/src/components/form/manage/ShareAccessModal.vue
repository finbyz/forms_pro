<script setup lang="ts">
import { Button, Dialog, MultiSelect, createResource } from "frappe-ui";
import { useTeam, type TeamMember } from "@/stores/team";
import { useUser } from "@/stores/user";
import { useManageForm, type SharedAccessUser } from "@/stores/form/manageForm";
import { computed, ref, watch } from "vue";
import Avatar from "@/components/ui/Avatar.vue";
import { toast } from "vue-sonner";

const teamStore = useTeam();
const userStore = useUser();
const manageFormStore = useManageForm();

const open = defineModel<boolean>({ required: true, default: false });

const effectiveTeamId = computed(() => {
    return (
        manageFormStore.formData?.linked_team_id ||
        teamStore.targetTeamId ||
        userStore.currentTeam?.name ||
        ""
    );
});

// Inline Add Member state
const showInlineAdd = ref(false);
const activeAddMode = ref<"existing" | "invite">("existing");
const selectedExistingUser = ref("");
const inviteEmail = ref("");
const isSubmitting = ref(false);

const availableUsersResource = createResource({
    url: "forms_pro.api.team.get_users_for_team_addition",
    auto: false,
    makeParams() {
        return {
            team_id: effectiveTeamId.value,
        };
    },
});

watch(open, (isOpen) => {
    if (isOpen) {
        showInlineAdd.value = false;
        selectedExistingUser.value = "";
        inviteEmail.value = "";
        selectedUsers.value = [];
        const teamId = effectiveTeamId.value;
        if (teamId) {
            teamStore.initialize(teamId);
            availableUsersResource.fetch({ team_id: teamId });
        }
    }
});

const existingUserOptions = computed(() => {
    const data = availableUsersResource.data;
    if (!Array.isArray(data)) return [];
    return data.map((u: any) => ({
        label: `${u.label} (${u.email})`,
        value: u.email,
    }));
});

const sharedAccessUsers = computed(() => manageFormStore.sharedAccessUsers);

const teamMembersNotSharedWith = computed(() => {
    return teamStore.teamMembers.filter((member: TeamMember) => {
        if (member.email === manageFormStore.formOwner) return false;
        return !sharedAccessUsers.value.some(
            (user: SharedAccessUser) => user.email === member.email
        );
    });
});

const multiSelectOptions = computed(() => {
    return teamMembersNotSharedWith.value.map((member: TeamMember) => {
        return {
            label: member.full_name || member.email,
            value: member.email,
        };
    });
});

const selectedUsers = ref<string[]>([]);

const DEFAULT_ACCESS_PERMISSIONS = {
    read: true,
    write: true,
    share: true,
    submit: false,
} as const;

const giveAccessToUsers = () => {
    selectedUsers.value.forEach((user) => {
        manageFormStore.addAccess(user, DEFAULT_ACCESS_PERMISSIONS);
    });
    toast.success("Access given to selected users successfully");
    selectedUsers.value = [];
};

const giveAccessToAllTeamMembers = () => {
    teamMembersNotSharedWith.value.forEach((member: TeamMember) => {
        manageFormStore.addAccess(member.email, DEFAULT_ACCESS_PERMISSIONS);
    });
    toast.success("Access given to all team members successfully");
    selectedUsers.value = [];
};

async function handleAddExistingUser(alsoGrantAccess: boolean = false) {
    if (!selectedExistingUser.value || !effectiveTeamId.value) return;
    isSubmitting.value = true;
    const userEmail = selectedExistingUser.value;

    try {
        await teamStore.addMemberToTeam(userEmail, effectiveTeamId.value);
        selectedExistingUser.value = "";
        showInlineAdd.value = false;

        // Refresh lists
        await teamStore.teamMembersResource.fetch({ team_id: effectiveTeamId.value });
        await availableUsersResource.fetch({ team_id: effectiveTeamId.value });

        if (alsoGrantAccess) {
            manageFormStore.addAccess(userEmail, DEFAULT_ACCESS_PERMISSIONS);
            toast.success("Member added to team and granted form access");
            open.value = false;
        } else {
            if (!selectedUsers.value.includes(userEmail)) {
                selectedUsers.value.push(userEmail);
            }
            toast.success("Team member added and selected for access");
        }
    } catch (err: any) {
        console.error(err);
    } finally {
        isSubmitting.value = false;
    }
}

async function handleSendInvitation() {
    const trimmed = inviteEmail.value.trim();
    if (!trimmed || !effectiveTeamId.value) return;
    isSubmitting.value = true;

    createResource({
        url: "forms_pro.api.team.invite_team_members",
        method: "POST",
        makeParams() {
            return {
                team_id: effectiveTeamId.value,
                emails: [trimmed],
            };
        },
        onSuccess() {
            toast.success(`Invitation sent to ${trimmed}`);
            inviteEmail.value = "";
            showInlineAdd.value = false;
            isSubmitting.value = false;
        },
        onError(error: Error) {
            toast.error("Failed to send invitation", {
                description: error.message,
            });
            isSubmitting.value = false;
        },
    }).submit();
}
</script>

<template>
    <Dialog
        v-model="open"
        :options="{
            title: 'Share Access',
            actions: [
                {
                    label: 'Share Access',
                    disabled: selectedUsers.length === 0,
                    onClick: () => {
                        giveAccessToUsers();
                        open = false;
                    },
                    variant: 'solid',
                },
            ],
        }"
    >
        <template #body-content>
            <div class="flex flex-col gap-3">
                <div class="flex items-center justify-between">
                    <p class="text-ink-gray-6 text-sm">
                        Add users from your team to grant access to this form.
                    </p>
                    <Button
                        v-if="teamMembersNotSharedWith.length > 0"
                        variant="ghost"
                        size="sm"
                        :icon-left="showInlineAdd ? 'x' : 'plus'"
                        @click="showInlineAdd = !showInlineAdd"
                    >
                        {{ showInlineAdd ? "Close" : "Add to Team" }}
                    </Button>
                </div>

                <!-- Inline Add Member Panel (visible when toggled OR when empty) -->
                <div
                    v-if="showInlineAdd || teamMembersNotSharedWith.length === 0"
                    class="p-4 rounded-xl bg-surface-gray-1 border border-outline-gray-2 flex flex-col gap-3"
                >
                    <!-- Empty State Header if 0 members -->
                    <div v-if="teamMembersNotSharedWith.length === 0" class="text-center pb-1">
                        <p class="text-sm font-semibold text-ink-gray-8">
                            {{
                                teamStore.teamMembers.length <= 1
                                    ? "No other team members found"
                                    : "All team members already have access"
                            }}
                        </p>
                        <p class="text-xs text-ink-gray-5 mt-0.5 max-w-sm mx-auto">
                            {{
                                teamStore.teamMembers.length <= 1
                                    ? "Add colleagues to your team below, then you can grant them access to this form."
                                    : "Everyone in your team already has permissions on this form."
                            }}
                        </p>
                    </div>

                    <!-- Mode Switcher Pills -->
                    <div class="flex gap-1.5 p-1 bg-surface-gray-2 rounded-lg w-fit">
                        <button
                            type="button"
                            class="px-2.5 py-1 text-xs font-medium rounded-md transition-colors"
                            :class="
                                activeAddMode === 'existing'
                                    ? 'bg-surface-white text-ink-gray-9 shadow-sm'
                                    : 'text-ink-gray-6 hover:text-ink-gray-9'
                            "
                            @click="activeAddMode = 'existing'"
                        >
                            Select System User
                        </button>
                        <button
                            type="button"
                            class="px-2.5 py-1 text-xs font-medium rounded-md transition-colors"
                            :class="
                                activeAddMode === 'invite'
                                    ? 'bg-surface-white text-ink-gray-9 shadow-sm'
                                    : 'text-ink-gray-6 hover:text-ink-gray-9'
                            "
                            @click="activeAddMode = 'invite'"
                        >
                            Invite by Email
                        </button>
                    </div>

                    <!-- System User Mode -->
                    <div v-if="activeAddMode === 'existing'" class="flex flex-col gap-2.5">
                        <div class="space-y-1">
                            <label class="text-xs font-medium text-ink-gray-7">Select User</label>
                            <select
                                v-model="selectedExistingUser"
                                class="w-full px-3 py-2 border border-outline-gray-2 rounded-lg text-sm bg-surface-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                            >
                                <option value="" disabled>Select a user to add...</option>
                                <option
                                    v-for="opt in existingUserOptions"
                                    :key="opt.value"
                                    :value="opt.value"
                                >
                                    {{ opt.label }}
                                </option>
                            </select>
                            <p
                                v-if="existingUserOptions.length === 0 && !availableUsersResource.loading"
                                class="text-xs text-ink-gray-5 italic pt-1"
                            >
                                No other unassigned users found in the system. Use "Invite by Email" to add new colleagues.
                            </p>
                        </div>
                        <div class="flex items-center gap-2 pt-1">
                            <Button
                                variant="solid"
                                size="sm"
                                icon-left="plus"
                                :loading="isSubmitting"
                                :disabled="!selectedExistingUser || isSubmitting"
                                @click="handleAddExistingUser(false)"
                            >
                                Add to Team
                            </Button>
                            <Button
                                v-if="teamMembersNotSharedWith.length === 0"
                                variant="outline"
                                size="sm"
                                icon-left="check"
                                :loading="isSubmitting"
                                :disabled="!selectedExistingUser || isSubmitting"
                                @click="handleAddExistingUser(true)"
                            >
                                Add & Grant Access
                            </Button>
                        </div>
                    </div>

                    <!-- Invite by Email Mode -->
                    <div v-else class="flex flex-col gap-2.5">
                        <div class="space-y-1">
                            <label class="text-xs font-medium text-ink-gray-7">Email Address</label>
                            <div class="flex items-center gap-2">
                                <input
                                    v-model="inviteEmail"
                                    type="email"
                                    placeholder="colleague@example.com"
                                    class="flex-1 px-3 py-2 border border-outline-gray-2 rounded-lg text-sm bg-surface-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                                    @keydown.enter.prevent="handleSendInvitation"
                                />
                                <Button
                                    variant="solid"
                                    size="sm"
                                    icon-left="plus"
                                    :loading="isSubmitting"
                                    :disabled="!inviteEmail.trim() || isSubmitting"
                                    @click="handleSendInvitation"
                                >
                                    Send Invite
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- When team members are available to add -->
                <div v-if="teamMembersNotSharedWith.length > 0" class="flex flex-col gap-2">
                    <Button
                        class="w-fit"
                        variant="outline"
                        size="sm"
                        icon-left="plus"
                        @click="
                            () => {
                                giveAccessToAllTeamMembers();
                                open = false;
                            }
                        "
                    >
                        Give Access to All Team Members ({{ teamMembersNotSharedWith.length }})
                    </Button>
                    <MultiSelect
                        :options="multiSelectOptions"
                        v-model="selectedUsers"
                        placeholder="Select team members..."
                    >
                        <template #option="{ item }">
                            <Avatar :userId="item.value" size="sm" />
                            <span class="text-ink-gray-8 text-sm ml-2">{{ item.label }}</span>
                        </template>
                    </MultiSelect>
                </div>
            </div>
        </template>
    </Dialog>
</template>
