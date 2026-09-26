import { createResource } from "frappe-ui";

export type LanguageOption = { value: string; label: string };

/**
 * The enabled languages, fetched once per page.
 *
 * Shared between the Language field itself and the builder's "Default value"
 * picker, so both offer exactly the same list and neither refetches it. The
 * value is Frappe's `language_code` ("de"); the label is the native name
 * ("Deutsch"), which is what a person recognises.
 */
let cache: Promise<LanguageOption[]> | null = null;

export function fetchLanguages(): Promise<LanguageOption[]> {
  if (!cache) {
    cache = createResource({ url: "forms_pro.api.form.get_languages" })
      .fetch()
      .then((data: LanguageOption[]) => data ?? [])
      .catch(() => {
        cache = null; // let a later caller retry rather than cache the failure
        return [] as LanguageOption[];
      });
  }
  return cache;
}
