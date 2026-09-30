import { describe, expect, it, vi } from "vitest";

/**
 * The registry is only consulted for the `isBoolean` flag, but importing it
 * pulls in every field component and, through them, frappe-ui's unbundled
 * sources — which this runner cannot load. The types used below are recognised
 * by name, so an empty registry is faithful.
 */
vi.mock("@/config/fieldTypes", () => ({ getFieldTypeDef: () => undefined }));

import {
  getFieldnamesInSection,
  getGovernedFieldnames,
  shouldFieldBeVisible,
} from "@/utils/conditionals";
import type { FormField } from "@/types/formfield";

const field = (fieldname: string, extra: Partial<FormField> = {}): FormField =>
  ({ fieldname, label: fieldname, fieldtype: "Data", ...extra } as FormField);

const step = (fieldname: string): FormField =>
  ({ fieldname, label: fieldname, fieldtype: "Page Break" } as FormField);

const showWhen = (trigger: string, value: string, target: string) =>
  JSON.stringify({
    conditions: [{ fieldname: trigger, operator: "Is", value }],
    action: "Show Field",
    target_field: target,
  });

/**
 * Mirrors the shape that surfaced the bug: a switch sitting in the middle of
 * "Company Information", with two plain fields after it.
 */
const form = (): FormField[] => [
  step("section_1"),
  field("first_name"),
  step("section_2"),
  field("data_2"),
  field("switch", { fieldtype: "Switch" }),
  field("textarea"),
  field("customer"),
  step("section_3"),
  field("expected_users"),
];

const visible = (fields: FormField[], values: Record<string, any>) =>
  fields.filter((f) => shouldFieldBeVisible(f, values, fields)).map((f) => f.fieldname);

describe("section membership", () => {
  it("collects the fields between one separator and the next", () => {
    expect(getFieldnamesInSection("section_2", form())).toEqual([
      "data_2",
      "switch",
      "textarea",
      "customer",
    ]);
  });
});

describe("a rule targeting a step", () => {
  it("governs every field in that step", () => {
    expect(getGovernedFieldnames("section_2", form(), ["first_name"])).toEqual([
      "data_2",
      "switch",
      "textarea",
      "customer",
    ]);
  });

  /**
   * The reported bug. Answering the switch cannot be a precondition for seeing
   * the switch, and the partial reading it used to get — "everything after the
   * trigger" — silently hid Company Address and Customer.
   */
  it("governs nothing when its own trigger sits inside that step", () => {
    expect(getGovernedFieldnames("section_2", form(), ["switch"])).toEqual([]);
  });

  it("leaves the trigger's neighbours alone", () => {
    const fields = form();
    fields[4].conditional_logic = showWhen("switch", "1", "section_2");

    expect(visible(fields, { switch: 0 })).toContain("textarea");
    expect(visible(fields, { switch: 0 })).toContain("customer");
  });
});

describe("a rule targeting a single field", () => {
  it("shows it only once the condition holds", () => {
    const fields = form();
    fields[4].conditional_logic = showWhen("switch", "1", "customer");

    expect(visible(fields, { switch: 0 })).not.toContain("customer");
    expect(visible(fields, { switch: 1 })).toContain("customer");
    expect(visible(fields, { switch: 0 })).toContain("textarea");
  });
});

describe("a rule triggered from outside the step it targets", () => {
  it("hides the whole step until the condition holds", () => {
    const fields = form();
    fields[1].conditional_logic = JSON.stringify({
      conditions: [{ fieldname: "first_name", operator: "Is", value: "yes" }],
      action: "Show Field",
      target_field: "section_2",
    });

    const hidden = visible(fields, { first_name: "no" });
    expect(hidden).not.toContain("data_2");
    expect(hidden).not.toContain("switch");
    expect(hidden).not.toContain("customer");
    expect(hidden).toContain("expected_users");

    expect(visible(fields, { first_name: "yes" })).toContain("customer");
  });
});

describe("boolean answers", () => {
  /**
   * Switches and checkboxes are handed `toBoolean(value)`. The form holds `""`
   * for a blank answer and a DocType's Check default arrives as `"0"`; handed
   * over raw, Vue cast `""` to true on the switch's Boolean prop and `"0"` was
   * drawn ticked, so what the visitor saw was not what got submitted.
   */
  it("reads the values the form actually holds", async () => {
    const { toBoolean } = await import("@/utils/conditionals");
    expect(toBoolean("")).toBe(false);
    expect(toBoolean("0")).toBe(false);
    expect(toBoolean(0)).toBe(false);
    expect(toBoolean(null)).toBe(false);
    expect(toBoolean("1")).toBe(true);
    expect(toBoolean(true)).toBe(true);
  });
});
