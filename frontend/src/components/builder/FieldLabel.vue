<script setup lang="ts">

defineProps<{
    field: {
        label?: string;
        reqd?: boolean;
    };
    inEditMode: boolean;
}>();

const emit = defineEmits<{
    "update:label": [value: string];
}>();
</script>

<template>
    <div class="flex gap-2 items-start">
        <input
            v-if="inEditMode"
            placeholder="Label"
            type="text"
            :value="field.label"
            @input="emit('update:label', ($event.target as HTMLInputElement).value)"
            class="bg-transparent border-none outline-none text-base focus:ring-0 w-full px-0 py-1"
        />
        <label class="text-base" v-else>{{ field.label }}</label>
        <!--
          Only mandatory fields carry the asterisk. Without the guard every
          field on the live form looked required, so the marker said nothing
          and visitors could not tell what they actually had to fill in.
        -->
        <span v-if="field.reqd" class="flex items-center" title="Mandatory">
            <lucide-asterisk class="w-4 h-4 text-red-400" aria-hidden="true" />
            <span class="sr-only">required</span>
        </span>
    </div>
</template>
