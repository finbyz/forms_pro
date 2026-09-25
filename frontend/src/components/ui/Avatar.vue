<script setup lang="ts">
import { Avatar as FrappeAvatar, Tooltip } from "frappe-ui";
import { getUser } from "@/utils/user";
import type { GetUserBasicResponse } from "@/utils/user";
import { ref, watch } from "vue";

const props = withDefaults(
    defineProps<{
        userId?: string | null;
        size?: "xs" | "sm" | "md" | "lg" | "xl" | "2xl" | "3xl";
        variant?: "default" | "outline" | "filled";
        shape?: "circle" | "square";
        className?: string;
        disabled?: boolean;
    }>(),
    {
        userId: "",
        size: "md",
        variant: "default",
        shape: "circle",
        disabled: false,
    }
);

const user = ref<GetUserBasicResponse | null>(null);

watch(
    () => props.userId,
    async (newId) => {
        if (newId) {
            user.value = await getUser(newId);
        } else {
            user.value = null;
        }
    },
    { immediate: true }
);
</script>

<template>
    <Tooltip
        v-if="props.userId"
        :disabled="disabled"
        :text="user?.full_name || props.userId"
        placement="bottom"
    >
        <FrappeAvatar
            :size="size"
            :shape="shape"
            :image="user?.user_image ?? undefined"
            :label="user?.full_name || props.userId"
        />
    </Tooltip>
</template>
