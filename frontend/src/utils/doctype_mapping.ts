/**
 * Maps a Frappe DocType field onto the equivalent Forms Pro field type.
 *
 * Returns `undefined` only for types that genuinely have no place on a form
 * (layout breaks, buttons). Callers must not fall back to the raw Frappe
 * fieldtype: it is not a Forms Pro type, and the renderer cannot draw it.
 *
 * Kept free of the component registry (which pulls in frappe-ui) so the mapping
 * can be unit tested on its own.
 */
import { Fieldtype } from "@/types/FormsPro/form_field.types";

// Maps Frappe DocType fieldtypes to the equivalent Forms Pro fieldtype.
// Used when importing fields from an existing DocType into a form.
export const mapDoctypeFieldForForm = (
  fieldtype: string,
  options?: string | null
): string | undefined => {
  // Frappe encodes "this Data column is an email / phone" in `options`.
  if (fieldtype === "Data" && options) {
    const semantic = options.trim().toLowerCase();
    if (semantic === "email") return Fieldtype.EMAIL;
    if (semantic === "phone") return Fieldtype.PHONE;
    if (semantic === "url") return Fieldtype.URL;
  }

  const FRAPPE_TO_FORM_TYPE: Partial<Record<string, Fieldtype>> = {
    Autocomplete: Fieldtype.DATA,
    Attach: Fieldtype.ATTACH,
    "Attach Image": Fieldtype.ATTACH,
    Check: Fieldtype.CHECKBOX,
    Currency: Fieldtype.NUMBER,
    Data: Fieldtype.DATA,
    Date: Fieldtype.DATE,
    Datetime: Fieldtype.DATE_TIME,
    Float: Fieldtype.NUMBER,
    "HTML Editor": Fieldtype.TEXT_EDITOR,
    Int: Fieldtype.NUMBER,
    Link: Fieldtype.LINK,
    "Long Text": Fieldtype.TEXTAREA,
    "Markdown Editor": Fieldtype.TEXT_EDITOR,
    Password: Fieldtype.PASSWORD,
    Percent: Fieldtype.NUMBER,
    Phone: Fieldtype.PHONE,
    Rating: Fieldtype.RATING,
    // A Frappe "Read Only" column is a Data value the user may not edit. It was
    // falling through this map, so importing Supplier's Mobile/Email -- both of
    // which are "Read Only", not "Data" -- produced a field with an unknown
    // type that rendered as an Attach box.
    "Read Only": Fieldtype.DATA,
    Select: Fieldtype.SELECT,
    "Small Text": Fieldtype.TEXTAREA,
    Table: Fieldtype.TABLE,
    Text: Fieldtype.TEXTAREA,
    "Text Editor": Fieldtype.TEXT_EDITOR,
    Time: Fieldtype.TIME_PICKER,
    // Frappe types with no dedicated widget here; a text box holds the value
    // safely rather than leaving the field unmapped.
    Barcode: Fieldtype.DATA,
    Code: Fieldtype.TEXTAREA,
    Color: Fieldtype.DATA,
    Duration: Fieldtype.DATA,
    "Dynamic Link": Fieldtype.DATA,
    Icon: Fieldtype.DATA,
    JSON: Fieldtype.TEXTAREA,
    Signature: Fieldtype.DATA,
    "Table MultiSelect": Fieldtype.MULTISELECT,
  };

  return FRAPPE_TO_FORM_TYPE[fieldtype];
};
