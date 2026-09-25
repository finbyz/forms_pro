<script setup lang="ts">
import { useUser, type UserTeam } from "@/stores/user";
import { Popover, TextInput, Button } from "frappe-ui";
import { computed, inject, ref } from "vue";
import { useRouter } from "vue-router";
import CreateTeamDialog from "@/components/team/CreateTeamDialog.vue";
import TeamSwitcherItem from "@/components/team/TeamSwitcherItem.vue";
import TeamLogo from "@/components/team/TeamLogo.vue";

const router = useRouter();
const isSidebarCollapsed = inject("isSidebarCollapsed");

const showCreateTeamDialog = ref(false);
const searchQuery = ref("");
const userStore = useUser();

const filteredOtherTeams = computed<UserTeam[]>(() => {
    const teams =
        userStore.userTeams?.filter(
            (team) =>
                team.name !== userStore.currentTeam?.name &&
                team.team_name.toLowerCase().includes(searchQuery.value.trim().toLowerCase())
        ) ?? [];
    return teams;
});
</script>
<template>
    <CreateTeamDialog v-model="showCreateTeamDialog" />
    <div class="w-full min-w-0">
        <Popover
            v-if="userStore.currentTeam"
            placement="bottom-start"
            popover-class="mt-1 shadow-2xl rounded-xl border border-outline-gray-modals bg-surface-modal z-50"
        >
            <template #target="{ togglePopover, isOpen }">
                <div
                    @click="togglePopover"
                    class="flex items-center gap-2 p-2 rounded cursor-pointer transition-colors duration-150 ease-[cubic-bezier(0.4, 0, 0.2, 1)] hover:bg-surface-gray-2 w-full min-w-0"
                    :class="{ 'bg-surface-white': isOpen, 'px-1.5 ': isSidebarCollapsed }"
                >
                    <TeamLogo
                        v-if="isSidebarCollapsed"
                        :team-name="userStore.currentTeam?.team_name"
                        :logo-url="userStore.currentTeam?.logo ?? null"
                    />
                    <div v-else class="flex items-center gap-2 justify-between w-full">
                        <TeamSwitcherItem
                            :label="userStore.currentTeam!.team_name"
                            :logo-url="userStore.currentTeam?.logo ?? null"
                        />
                        <lucide-chevrons-up-down class="text-ink-gray-6 size-4 shrink-0" aria-hidden="true" />
                    </div>
                </div>
            </template>
            <template #body="{ close }">
                <div class="w-64 flex flex-col p-1.5">
                    <!-- Search Input -->
                    <div class="p-1 mb-1">
                        <TextInput
                            v-model="searchQuery"
                            placeholder="Search Team..."
                            size="sm"
                            variant="subtle"
                            class="w-full"
                        >
                            <template #prefix>
                                <lucide-search class="text-ink-gray-5 size-3.5" aria-hidden="true" />
                            </template>
                        </TextInput>
                    </div>

                    <!-- Teams List (Scrollable) -->
                    <div class="px-2 py-1 text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
                        Switch Team
                    </div>
                    <div class="overflow-y-auto max-h-52 flex flex-col gap-0.5 py-0.5">
                        <div
                            v-for="team in filteredOtherTeams"
                            :key="team.name"
                            @click="() => { userStore.switchTeam(team); close(); }"
                            class="flex items-center gap-2.5 p-2 rounded-lg cursor-pointer hover:bg-surface-gray-2 transition-colors text-sm text-ink-gray-8"
                        >
                            <TeamLogo :team-name="team.team_name" :logo-url="team.logo" size="sm" />
                            <span class="truncate flex-1 font-medium">{{ team.team_name }}</span>
                        </div>
                        <div
                            v-if="filteredOtherTeams.length === 0"
                            class="py-3 text-center text-xs text-ink-gray-5 italic"
                        >
                            {{ searchQuery ? 'No matching teams' : 'No other teams available' }}
                        </div>
                    </div>

                    <div class="my-1.5 border-t border-outline-gray-2"></div>

                    <!-- Action Links -->
                    <div class="flex flex-col gap-0.5">
                        <Button
                            variant="ghost"
                            size="sm"
                            class="w-full !justify-start text-sm"
                            icon-left="users"
                            @click="() => { router.push('/team'); close(); }"
                        >
                            Manage Team
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            class="w-full !justify-start text-sm"
                            icon-left="plus"
                            @click="() => { showCreateTeamDialog = true; close(); }"
                        >
                            Create New Team
                        </Button>
                    </div>
                </div>
            </template>
        </Popover>
        <div
            v-else
            @click="router.push('/team')"
            class="flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-surface-gray-2 text-sm text-ink-gray-7"
        >
            <div class="size-6 rounded bg-surface-gray-3 flex items-center justify-center text-xs font-semibold text-ink-gray-7">
                T
            </div>
            <span class="font-medium truncate">Team Settings</span>
        </div>
    </div>
</template>
