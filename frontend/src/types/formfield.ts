export { Fieldtype } from "@/types/FormsPro/form_field.types";
import { Fieldtype } from "@/types/FormsPro/form_field.types";

export type FormField = {
  label: string;
  fieldname: string;
  fieldtype: Fieldtype;
  description?: string;
  reqd?: boolean;
  hidden?: boolean;
  options?: string;
  default?: string;
  idx?: number;
  conditional_logic?: string;
  field_key?: string;
  source_type?: "Custom" | "Mapped";
  target_field?: string;
  mapping_type?: "Direct" | "Expression" | "Webhook";
  row_index?: number;
  column_index?: number;
  cell_index?: number;
};
