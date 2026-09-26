import { describe, expect, it } from "vitest";
import {
  groupFieldsIntoSteps,
  insertFieldAtStepEnd,
  removeStepKeepFields,
  renameStep,
} from "@/utils/form_steps";
import type { FormField } from "@/types/formfield";

const field = (fieldname: string, row: number): FormField =>
  ({ fieldname, label: fieldname, fieldtype: "Data", row_index: row } as FormField);

const pageBreak = (label: string, row: number): FormField =>
  ({ fieldname: label, label, fieldtype: "Page Break", row_index: row } as FormField);

describe("grouping fields into steps", () => {
  it("splits on Page Breaks", () => {
    const steps = groupFieldsIntoSteps([
      field("a", 0),
      pageBreak("Step 2", 1),
      field("b", 2),
    ]);
    expect(steps.map((s) => s.fields.map((f) => f.fieldname))).toEqual([["a"], ["b"]]);
  });

  /**
   * An empty step on the live form is a page with a heading, no fields and a
   * Next button — nothing for the visitor to do. The builder still shows it so
   * it can be filled or removed; only the rendered form skips it.
   */
  it("drops an empty middle step when asked", () => {
    const steps = groupFieldsIntoSteps(
      [
        field("a", 0),
        pageBreak("Empty", 1),
        pageBreak("Last", 2),
        field("b", 3),
      ],
      { dropEmptySteps: true }
    );
    expect(steps.map((s) => s.fields.map((f) => f.fieldname))).toEqual([["a"], ["b"]]);
  });

  it("keeps the last step even when empty, so Submit still renders", () => {
    const steps = groupFieldsIntoSteps([field("a", 0), pageBreak("Trailing", 1)], {
      dropEmptySteps: true,
      alwaysIncludeTrailing: true,
    });
    expect(steps).toHaveLength(2);
    expect(steps[1].fields).toEqual([]);
  });

  it("never returns zero steps, even for a form with nothing in it", () => {
    const steps = groupFieldsIntoSteps([pageBreak("One", 0), pageBreak("Two", 1)], {
      dropEmptySteps: true,
      alwaysIncludeTrailing: true,
    });
    expect(steps.length).toBeGreaterThan(0);
  });

  it("leaves empty steps alone by default, for the builder", () => {
    const steps = groupFieldsIntoSteps([
      field("a", 0),
      pageBreak("Empty", 1),
      pageBreak("Last", 2),
      field("b", 3),
    ]);
    expect(steps).toHaveLength(3);
  });
});

describe("moving a field between steps", () => {
  it("places the field inside the target step", () => {
    const fields = [
      field("a", 0),
      field("keep", 1),
      pageBreak("Step 2", 2),
      field("b", 3),
    ];
    const moving = fields[0];

    fields.splice(fields.indexOf(moving), 1);
    insertFieldAtStepEnd(fields, moving, 1, true);

    const steps = groupFieldsIntoSteps(fields);
    expect(steps[0].fields.map((f) => f.fieldname)).toEqual(["keep"]);
    expect(steps[1].fields.map((f) => f.fieldname)).toEqual(["b", "a"]);
  });

  /**
   * Emptying the first step leaves its Page Break at the head of the list,
   * which this representation reads as *naming* the remaining step rather than
   * separating two. The empty step therefore collapses — which is what we want
   * anyway: a step with nothing in it is not a page worth showing.
   */
  it("collapses the first step when its last field leaves", () => {
    const fields = [field("a", 0), pageBreak("Step 2", 1), field("b", 2)];
    const moving = fields[0];

    fields.splice(fields.indexOf(moving), 1);
    insertFieldAtStepEnd(fields, moving, 1, true);

    const steps = groupFieldsIntoSteps(fields);
    expect(steps).toHaveLength(1);
    expect(steps[0].fields.map((f) => f.fieldname)).toEqual(["b", "a"]);
  });

  it("moves a field back to the first step", () => {
    const fields = [field("a", 0), pageBreak("Step 2", 1), field("b", 2)];
    const moving = fields[2];

    fields.splice(fields.indexOf(moving), 1);
    insertFieldAtStepEnd(fields, moving, 0, true);

    const steps = groupFieldsIntoSteps(fields);
    expect(steps[0].fields.map((f) => f.fieldname)).toContain("b");
  });
});

describe("removing a step keeps the remaining step's name", () => {
  /**
   * The reported sequence: rename step 1 to "Contact Details", move step 2's
   * fields into it, then delete step 2. The name used to revert to "Step 1",
   * because renaming step 1 stores the label on a leading Page Break and the
   * cleanup pass then discarded that row as orphaned.
   */
  it("keeps a renamed first step's label after the other step is deleted", () => {
    const fields: FormField[] = [
      field("name", 0),
      pageBreak("Step 2", 1),
      field("phone", 2),
    ];

    renameStep(fields, 0, "Contact Details");
    expect(groupFieldsIntoSteps(fields)[0].label).toBe("Contact Details");

    const steps = groupFieldsIntoSteps(fields);
    removeStepKeepFields(fields, steps, 1);

    const after = groupFieldsIntoSteps(fields, { labelFallback: (n) => `Step ${n}` });
    expect(after).toHaveLength(1);
    expect(after[0].label).toBe("Contact Details");
    expect(after[0].fields.map((f) => f.fieldname)).toEqual(["name", "phone"]);
  });

  it("still drops a leading Page Break that carries no name", () => {
    const fields: FormField[] = [
      pageBreak("", 0),
      field("name", 1),
      pageBreak("Step 2", 2),
      field("phone", 3),
    ];

    const steps = groupFieldsIntoSteps(fields);
    removeStepKeepFields(fields, steps, 1);

    expect(fields.some((f) => f.fieldtype === "Page Break")).toBe(false);
  });
});
