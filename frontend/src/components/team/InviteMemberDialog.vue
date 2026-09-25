<script setup lang="ts">
import { ref, computed, watch } from "vue";
import * as z from "zod";
import {
    Dialog,
    FormControl,
    ErrorMessage,
    Button,
    Avatar as FrappeAvatar,
    createResource,
} from "frappe-ui";
import { useTeam } from "@/stores/team";
import { toast } from "vue-sonner";

const props = defineProps<{
    teamId?: string;
}>();

const team = useTeam();
const open = defineModel<boolean>({ required: true, default: false });

const effectiveTeamId = computed(() => props.teamId || team.targetTeamId);
const isAddingUser = ref(false);

const activeMode = ref<"existing" | "invite">("existing");
const selectedExistingUser = ref<string>("");

const availableUsersResource = createResource({
    url: "forms_pro.api.team.get_users_for_team_addition",
    auto: false,
    makeParams() {
        return {
            team_id: effectiveTeamId.value,
        };
    },
});

watch(
    () => [open.value, effectiveTeamId.value] as const,
    ([isOpen, id]) => {
        if (isOpen && id) {
            availableUsersResource.fetch({ team_id: id });
        }
    },
    { immediate: true }
);

const existingUserOptions = computed(() => {
    const data = availableUsersResource.data;
    if (!Array.isArray(data)) return [];
    return data.map((u: any) => ({
        label: `${u.label} (${u.email})`,
        value: u.email,
    }));
});

async function addSelectedExistingUser() {
    if (!selectedExistingUser.value || !effectiveTeamId.value) return;
    isAddingUser.value = true;
    try {
        await team.addMemberToTeam(selectedExistingUser.value, effectiveTeamId.value);
        selectedExistingUser.value = "";
        open.value = false;
    } catch (err) {
        console.error(err);
    } finally {
        isAddingUser.value = false;
    }
}

const inviteEmails = ref<string[]>([]);
const emailInput = ref("");
const emailInputError = ref<string>("");

const emailSchema = z.email();

function addInviteEmail() {
    const trimmed = emailInput.value.trim();
    if (!trimmed) return;
    const result = emailSchema.safeParse(trimmed);
    if (!result.success) {
        emailInputError.value = result.error.issues.map((issue) => issue.message).join(", ");
        return;
    }
    if (inviteEmails.value.includes(result.data)) {
        emailInputError.value = "Email already added";
        return;
    }
    inviteEmails.value.push(result.data);
    emailInput.value = "";
    emailInputError.value = "";
}

function removeInviteEmail(email: string) {
    inviteEmails.value = inviteEmails.value.filter((e) => e !== email);
}

function sendInvitationEmails() {
    if (!effectiveTeamId.value) return;
    isAddingUser.value = true;
    createResource({
        url: "forms_pro.api.team.invite_team_members",
        method: "POST",
        makeParams() {
            return {
                team_id: effectiveTeamId.value,
                emails: inviteEmails.value,
            };
        },
        onSuccess: () => {
            toast.success("Invitations sent successfully");
            open.value = false;
            inviteEmails.value = [];
            isAddingUser.value = false;
        },
        onError: (error: Error) => {
            toast.error("Failed to send invitations", {
                description: error.message,
            });
            isAddingUser.value = false;
        },
    }).submit();
}
</script>
<template>
    <Dialog
        v-model="open"
        :options="{
            title: 'Add Members to Team',
            size: 'lg',
            actions: [
                {
                    label:
                        activeMode === 'existing'
                            ? isAddingUser
                                ? 'Adding...'
                                : 'Add User to Team'
                            : isAddingUser
                              ? 'Sending...'
                              : 'Send Invitations',
                    disabled:
                        isAddingUser ||
                        (activeMode === 'existing'
                            ? !selectedExistingUser
                            : inviteEmails.length === 0),
                    variant: 'solid',
                    onClick: () => {
                        if (activeMode === 'existing') {
                            addSelectedExistingUser();
                        } else {
                            sendInvitationEmails();
                        }
                    },
                },
            ],
        }"
    >
        <template #body-content>
            <div class="flex flex-col gap-4">
                <!-- Mode Switcher -->
                <div class="flex gap-2 p-1 bg-surface-gray-2 rounded-lg w-fit">
                    <button
                        type="button"
                        class="px-3 py-1 text-sm font-medium rounded-md transition-colors"
                        :class="
                            activeMode === 'existing'
                                ? 'bg-surface-white text-ink-gray-9 shadow-sm'
                                : 'text-ink-gray-5 hover:text-ink-gray-8'
                        "
                        @click="activeMode = 'existing'"
                    >
                        Select System User
                    </button>
                    <button
                        type="button"
                        class="px-3 py-1 text-sm font-medium rounded-md transition-colors"
                        :class="
                            activeMode === 'invite'
                                ? 'bg-surface-white text-ink-gray-9 shadow-sm'
                                : 'text-ink-gray-5 hover:text-ink-gray-8'
                        "
                        @click="activeMode = 'invite'"
                    >
                        Invite by Email
                    </button>
                </div>

                <!-- Existing User Mode -->
                <div v-if="activeMode === 'existing'" class="flex flex-col gap-2">
                    <label class="text-sm font-medium text-ink-gray-7">Select an existing system user</label>
                    <select
                        v-model="selectedExistingUser"
                        class="w-full px-3 py-2 border rounded-md text-sm bg-surface-white focus:outline-none focus:ring-1 focus:ring-primary-500"
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
                    <p v-if="existingUserOptions.length === 0" class="text-xs text-ink-gray-5 italic">
                        No other system users found, or all users are already in this team. Use "Invite by Email" to invite external users.
                    </p>
                </div>

                <!-- Invite Mode -->
                <div v-else class="flex flex-col gap-3">
                    <div class="flex items-center gap-2">
                        <FormControl
                            v-model="emailInput"
                            label="Invite by Email"
                            type="email"
                            variant="outline"
                            class="flex-1"
                            @keydown.enter.prevent="addInviteEmail"
                            description="Enter email and press Enter"
                        />
                        <Button size="sm" icon-left="plus" @click="addInviteEmail"> Add </Button>
                    </div>
                    <ErrorMessage :message="emailInputError" />
                    <ul v-if="inviteEmails.length" class="flex flex-col gap-2">
                        <span class="text-base font-medium text-ink-gray-8">Recipients</span>
                        <li v-for="email in inviteEmails" :key="email" class="flex items-center gap-2">
                            <FrappeAvatar :label="email" size="sm" />
                            <span class="text-sm text-ink-gray-6 flex-1">{{ email }}</span>
                            <Button
                                icon="trash"
                                variant="subtle"
                                size="sm"
                                @click="removeInviteEmail(email)"
                            />
                        </li>
                    </ul>
                </div>
            </div>
        </template>
    </Dialog>
</template>
