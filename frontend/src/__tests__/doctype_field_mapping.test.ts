import { describe, expect, it } from "vitest";
import { mapDoctypeFieldForForm } from "@/utils/doctype_mapping";
import { Fieldtype } from "@/types/FormsPro/form_field.types";

/**
 * Frappe marks a Data column as an email or phone via `options`, and relies on
 * that for validation. Importing a DocType field must carry those semantics
 * across, or e.g. Lead.email_id arrives as a plain text box that accepts
 * anything.
 */
describe("mapDoctypeFieldForForm", () => {
  it("maps Data + options 'Email' to the Email field type", () => {
    expect(mapDoctypeFieldForForm("Data", "Email")).toBe(Fieldtype.EMAIL);
  });

  it("maps Data + options 'Phone' to the Phone field type", () => {
    expect(mapDoctypeFieldForForm("Data", "Phone")).toBe(Fieldtype.PHONE);
  });

  it("is case and whitespace tolerant, since options are author-entered", () => {
    expect(mapDoctypeFieldForForm("Data", " email ")).toBe(Fieldtype.EMAIL);
    expect(mapDoctypeFieldForForm("Data", "PHONE")).toBe(Fieldtype.PHONE);
  });

  it("leaves a plain Data field alone", () => {
    expect(mapDoctypeFieldForForm("Data")).toBe(Fieldtype.DATA);
    expect(mapDoctypeFieldForForm("Data", null)).toBe(Fieldtype.DATA);
  });

  it("does not treat a Select option list as a semantic marker", () => {
    // A Select's options are real choices, not an Email/Phone marker.
    expect(mapDoctypeFieldForForm("Select", "Email\nPhone")).toBe(Fieldtype.SELECT);
  });

  it("still maps a native Phone column", () => {
    expect(mapDoctypeFieldForForm("Phone")).toBe(Fieldtype.PHONE);
  });

  it("maps a Frappe 'Read Only' column to a text field, not nothing", () => {
    // Supplier.mobile_no and .email_id are fieldtype "Read Only", not "Data".
    // Unmapped, they fell back to the raw Frappe type and rendered as an
    // Attach box on the form.
    expect(mapDoctypeFieldForForm("Read Only")).toBe(Fieldtype.DATA);
  });

  it("leaves no common Frappe input type unmapped", () => {
    const INPUT_TYPES = [
      "Autocomplete", "Attach", "Attach Image", "Barcode", "Check", "Code",
      "Color", "Currency", "Data", "Date", "Datetime", "Duration",
      "Dynamic Link", "Float", "HTML Editor", "Icon", "Int", "JSON", "Link",
      "Long Text", "Markdown Editor", "Password", "Percent", "Phone", "Rating",
      "Read Only", "Select", "Signature", "Small Text", "Table",
      "Table MultiSelect", "Text", "Text Editor", "Time",
    ];
    const unmapped = INPUT_TYPES.filter((t) => !mapDoctypeFieldForForm(t));
    expect(unmapped, `unmapped Frappe types: ${unmapped.join(", ")}`).toEqual([]);
  });

  it("maps the other common Frappe types unchanged", () => {
    expect(mapDoctypeFieldForForm("Int")).toBe(Fieldtype.NUMBER);
    expect(mapDoctypeFieldForForm("Check")).toBe(Fieldtype.CHECKBOX);
    expect(mapDoctypeFieldForForm("Date")).toBe(Fieldtype.DATE);
    expect(mapDoctypeFieldForForm("Small Text")).toBe(Fieldtype.TEXTAREA);
  });
});
