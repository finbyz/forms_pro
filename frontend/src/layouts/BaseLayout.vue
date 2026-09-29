<template>
    <div class="flex h-screen w-full overflow-hidden">
        <Sidebar :sections="sidebarSections">
            <template #header>
                <TeamSwitcher />
            </template>
            <template #footer-items="{ isCollapsed }">
                <a
                    v-if="userStore.user?.has_desk_access"
                    href="/app"
                    aria-label="Back to Desk"
                    :title="isCollapsed ? 'Back to Desk' : undefined"
                    class="p-2 rounded-4 flex gap-2 items-center text-ink-gray-7 hover:bg-surface-gray-2 transition-base"
                    :class="{ '!p-1': isCollapsed }"
                >
                    <lucide-layout-dashboard class="size-5 shrink-0" aria-hidden="true" />
                    <span v-if="!isCollapsed" class="text-sm-medium">Back to Desk</span>
                </a>
                <Popover placement="top-start">
                    <template #target="{ togglePopover, isOpen }">
                        <div
                            @click="togglePopover"
                            class="p-2 z-10 rounded-4 flex gap-2 items-center hover:bg-surface-gray-2 cursor-pointer transition-base"
                            :class="{ 'bg-surface-gray-2': isOpen, '!p-1': isCollapsed }"
                        >
                            <Avatar
                                :disabled="true"
                                v-if="session.user"
                                :user-id="session.user"
                                size="lg"
                                shape="square"
                            />
                            <div v-if="!isCollapsed" class="flex items-center gap-2 min-w-0 flex-1">
                                <div class="flex flex-col gap-0.5 min-w-0 flex-1">
                                    <span class="text-sm-medium text-ink-gray-8 truncate">
                                        {{ session.full_name }}
                                    </span>
                                    <span class="text-xs text-ink-gray-5 truncate">{{ session.user }}</span>
                                </div>
                                <lucide-ellipsis-vertical class="size-4 text-ink-gray-5 shrink-0" aria-hidden="true" />
                            </div>
                        </div>
                    </template>
                    <template #body>
                        <div
                            class="flex flex-col gap-1 bg-surface-elevation-2 shadow-2xl rounded-6 mb-2 p-1"
                            :class="{ 'w-56': !isCollapsed }"
                        >
                            <Button
                                variant="ghost"
                                theme="red"
                                @click="session.logout.submit"
                                label="Log out"
                                icon-left="log-out"
                                size="sm"
                            />
                        </div>
                    </template>
                </Popover>
            </template>
        </Sidebar>
        <div class="p-6 flex-1 min-h-0 overflow-y-auto">
            <slot />
        </div>
    </div>
</template>
<script setup lang="ts">
import { session } from "@/data/session";
import { useUser } from "@/stores/user";
import { Popover, Sidebar, type SidebarProps } from "frappe-ui";
import type { PropType } from "vue";
import Avatar from "@/components/ui/Avatar.vue";
import TeamSwitcher from "@/components/team/TeamSwitcher.vue";

const userStore = useUser();

type SidebarSectionProps = NonNullable<SidebarProps["sections"]> extends (infer T)[] ? T : never;
type SidebarHeaderProps = NonNullable<SidebarProps["header"]>;

const props = defineProps({
    sidebarHeader: {
        type: Object as PropType<SidebarHeaderProps | null>,
        default: null,
    },
    sidebarSections: {
        type: Array as PropType<SidebarSectionProps[]>,
        default: () => [],
    },
});
</script>
