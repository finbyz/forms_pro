import { createResource } from "frappe-ui";
import type { Ref, ComputedRef } from "vue";
import { ref, watch } from "vue";

export type SelectOption = {
  label: string;
  value: string;
};

export type FieldForOptions = {
  fieldtype?: string;
  options?: string;
  [key: string]: unknown;
};

/**
 * Resolves options for Select and Link form fields.
 * Returns string[] for Select (newline-separated options), API result for Link, or raw options otherwise.
 */
export async function getFieldOptions(
  field: FieldForOptions
): Promise<string[] | SelectOption[] | string | ""> {
  if (!field?.options) {
    return "";
  }

  if (field.fieldtype === "Select" || field.fieldtype === "Multiselect") {
    return field.options.split("\n");
  }

  if (field.fieldtype === "Link") {
    const resource = createResource({
      url: "forms_pro.api.form.get_link_field_options",
      makeParams: () => ({
        doctype: field.options,
        filters: {},
        page_length: 999,
      }),
    });
    try {
      await resource.fetch();
    } catch {
      // A refused or failed lookup leaves the field with nothing to offer,
      // which is bad enough on its own -- it must not also take the page down
      // by rejecting inside the watcher that called this.
      return [];
    }
    return (resource.data ?? []) as string[] | SelectOption[];
  }

  return field.options;
}

/**
 * Composable to load and reactively track options for a Select/Link field.
 * Call load() or rely on automatic load on mount and when field type/options change.
 */
export function useFieldOptions(
  field: Ref<FieldForOptions> | ComputedRef<FieldForOptions>
) {
  // Always a list, never null. frappe-ui's select registers each option and
  // reads `.value` off it, so a null list -- or a null entry inside one --
  // crashes the whole page with "Cannot read properties of null".
  const options = ref<string[] | SelectOption[]>([]);

  const load = async () => {
    let result: unknown = [];
    try {
      result = await getFieldOptions(field.value);
    } catch {
      result = [];
    }
    options.value = Array.isArray(result)
      ? (result.filter((option) => option !== null && option !== undefined) as
          | string[]
          | SelectOption[])
      : [];
  };

  watch(
    () => [field.value.fieldtype, field.value.options],
    () => load(),
    { immediate: true }
  );

  return { options, load };
}
