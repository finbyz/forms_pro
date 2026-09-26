<script setup lang="ts">
/**
 * A dropdown you can type in.
 *
 * Link fields rendered as a plain `<select>`, which is fine for three options
 * and unusable for a Link to User or Contact: the browser's native list has no
 * search, so picking a value meant scrolling hundreds of rows.
 *
 * frappe-ui's Autocomplete is the same control the desk uses, so the behaviour
 * and styling are the ones people already know. It filters as you type and
 * renders at most `maxOptions` rows, which keeps a long list responsive.
 *
 * The field model is a plain value (the linked docname, or the Select option).
 * Autocomplete works in option objects, so this translates between the two.
 */
import { computed } from "vue";
import { Autocomplete } from "frappe-ui";
import type { SelectOption } from "@/utils/selectOptions";

type Option = { label: string; value: string };

const model = defineModel<string | number | null>();

const props = withDefaults(
    defineProps<{
        options?: string[] | SelectOption[] | null;
        disabled?: boolean;
        field?: Record<string, unknown>;
        placeholder?: string;
    }>(),
    { options: null, disabled: false, placeholder: "" }
);

/** Options arrive either as bare strings (Select) or {label, value} (Link). */
const normalised = computed<Option[]>(() => {
    const raw = props.options ?? [];
    return (raw as (string | SelectOption)[])
        .map((opt) =>
            typeof opt === "string"
                ? { label: opt, value: opt }
                : { label: opt.label ?? String(opt.value), value: String(opt.value) }
        )
        .filter((opt) => opt.value !== "");
});

/**
 * A search box over four options is noise; over four hundred it is the whole
 * point. Frappe's own Link control makes the same call.
 */
const SEARCH_THRESHOLD = 8;
const hideSearch = computed(() => normalised.value.length < SEARCH_THRESHOLD);

const placeholder = computed(
    () => props.placeholder || (props.field?.placeholder as string) || "Select option"
);

/** Autocomplete hands back the whole option; the form only wants its value. */
function onChange(selected: Option | null) {
    model.value = selected ? selected.value : null;
}
</script>

<template>
    <Autocomplete
        :options="normalised"
        :model-value="model ?? null"
        :placeholder="placeholder"
        :disabled="disabled"
        :hide-search="hideSearch"
        @update:model-value="onChange"
    />
</template>
