import { describe, expect, it } from "vitest";
import { placeBesideAbove } from "@/utils/form_layout";
import type { FormField } from "@/types/formfield";

function field(label: string, row: number, col = 0, cell = 0): FormField {
  return {
    label,
    fieldname: label.toLowerCase(),
    fieldtype: "Data",
    row_index: row,
    column_index: col,
    cell_index: cell,
  } as FormField;
}

const layout = (fields: FormField[]) =>
  fields.map((f) => `${f.label}@${f.row_index}.${f.column_index}.${f.cell_index}`);

describe("placeBesideAbove", () => {
  it("moves a field into the row above as a second column", () => {
    const first = field("First", 0);
    const second = field("Second", 1);
    const fields = [first, second];

    expect(placeBesideAbove(fields, second)).toBe(true);
    expect(layout(fields)).toEqual(["First@0.0.0", "Second@0.1.0"]);
  });

  it("appends to the right of an already multi-column row", () => {
    const a = field("A", 0, 0);
    const b = field("B", 0, 1);
    const c = field("C", 1);
    const fields = [a, b, c];

    expect(placeBesideAbove(fields, c)).toBe(true);
    expect(layout(fields)).toEqual(["A@0.0.0", "B@0.1.0", "C@0.2.0"]);
  });

  it("closes the gap left behind when the source row empties", () => {
    const a = field("A", 0);
    const b = field("B", 1);
    const c = field("C", 2);
    const fields = [a, b, c];

    placeBesideAbove(fields, b);

    // B joined row 0, so C's row 2 compacts down to row 1.
    expect(layout(fields)).toEqual(["A@0.0.0", "B@0.1.0", "C@1.0.0"]);
  });

  it("is a no-op for a field already on the first row", () => {
    const a = field("A", 0);
    const fields = [a];

    expect(placeBesideAbove(fields, a)).toBe(false);
    expect(layout(fields)).toEqual(["A@0.0.0"]);
  });

  it("is a no-op for a field that is not part of the form", () => {
    const a = field("A", 0);
    const stranger = field("Stranger", 1);

    expect(placeBesideAbove([a], stranger)).toBe(false);
  });

  it("round-trips: beside-above then back to its own row", () => {
    const a = field("A", 0);
    const b = field("B", 1);
    const fields = [a, b];

    placeBesideAbove(fields, b);
    expect(b.row_index).toBe(0);
    expect(b.column_index).toBe(1);

    // "Move to own row" is the inverse operation used by the eject button.
    b.row_index = 1;
    b.column_index = 0;
    b.cell_index = 0;
    expect(layout(fields)).toEqual(["A@0.0.0", "B@1.0.0"]);
  });
});
