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
 * Only enabled languages are offered, matching the desk.
 */
import { computed, onMounted, ref } from "vue";
import { Select, createResource } from "frappe-ui";

type LanguageOption = { value: string; label: string };

const model = defineModel<string | null>();

/**
 * Fallthrough attributes must not reach the <Select>.
 *
 * RenderField hands every field component `field`, `options`, `in-edit-mode`
 * and `placeholder`. Undeclared ones fall through to this component's root,
 * and Vue applies them *after* the template's own bindings -- so the parent's
 * `options` (which is `null`, because a Language field has no option string of
 * its own) replaced the language list built here. The control rendered, showed
 * its placeholder, and would not open, because a select with no options has
 * nothing to show.
 */
defineOptions({ inheritAttrs: false });

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

/**
 * Shared across every Language field on a form — a form with a language
 * picker per step should not fetch the same list repeatedly.
 */
let cache: Promise<LanguageOption[]> | null = null;

function fetchLanguages(): Promise<LanguageOption[]> {
  if (!cache) {
    cache = createResource({ url: "forms_pro.api.form.get_languages" })
      .fetch()
      .then((data: LanguageOption[]) => data ?? [])
      .catch(() => {
        cache = null; // let a later mount retry rather than cache the failure
        return [] as LanguageOption[];
      });
  }
  return cache;
}

const languages = ref<LanguageOption[]>([]);
const loading = ref(true);

onMounted(async () => {
  languages.value = await fetchLanguages();
  loading.value = false;
});

const options = computed(() => [
  { value: "", label: loading.value ? "Loading languages…" : "Select a language" },
  ...languages.value,
]);
</script>

<template>
  <Select v-model="model" :options="options" :disabled="disabled || loading" variant="outline" />
</template>
