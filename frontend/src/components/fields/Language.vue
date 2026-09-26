<script setup lang="ts">
/**
 * Language picker.
 *
 * Follows Frappe's own convention: the Language doctype is autonamed by
 * `language_code`, and `User.language` is a Link to it, so the value stored
 * here is the code ("de") while the visitor sees the native name ("Deutsch").
 * That keeps a submitted value usable anywhere Frappe already expects a
 * language, without a translation table of our own.
 *
 * Rendered through SearchSelect, the same searchable control used for Link
 * fields: this *is* a link to Language, and scrolling ~13 native names with no
 * search was the odd one out.
 *
 * Only enabled languages are offered, matching the desk.
 */
import { onMounted, ref } from "vue";
import SearchSelect from "@/components/fields/SearchSelect.vue";
import { fetchLanguages, type LanguageOption } from "@/utils/languages";

const model = defineModel<string | null>();

withDefaults(
    defineProps<{
        disabled?: boolean;
        /** Accepted and ignored: the list is fetched, not passed in. */
        options?: unknown;
        field?: Record<string, unknown>;
        inEditMode?: boolean;
        placeholder?: string;
    }>(),
    { disabled: false, options: null, field: undefined, inEditMode: false, placeholder: "" }
);

const languages = ref<LanguageOption[]>([]);
const loading = ref(true);

onMounted(async () => {
    languages.value = await fetchLanguages();
    loading.value = false;
});
</script>

<template>
    <SearchSelect
        v-model="model"
        :options="languages"
        :disabled="disabled || loading"
        :placeholder="loading ? 'Loading languages…' : 'Select a language'"
    />
</template>
