import {
  FIELD_TYPE_DEFINITIONS,
  FIELD_TYPE_MAP,
  getFieldTypeDef,
} from "@/config/fieldTypes";
import type { FieldTypeDefinition } from "@/config/fieldTypes";
import { Fieldtype } from "@/types/FormsPro/form_field.types";
import type { Component } from "vue";

// Re-export the registry under the names the rest of the codebase uses
export {
  FIELD_TYPE_DEFINITIONS as formFields,
  getFieldTypeDef,
  FIELD_TYPE_MAP,
};
export type { FieldTypeDefinition as FormFields };

// Subset type used by RenderField.vue
export type FormFieldType = {
  component: Component;
  props: Record<string, unknown>;
};

export { mapDoctypeFieldForForm } from "@/utils/doctype_mapping";


// Pure layout-grid helpers live in form_layout.ts (unit-testable without
// pulling in the component registry); re-exported here for existing imports.
export {
  isHeading,
  isPageBreak,
  isDisplayOnly,
  scrubFieldname,
  lastRowIndex,
  compact,
} from "@/utils/form_layout";
