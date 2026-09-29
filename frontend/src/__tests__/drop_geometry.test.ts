import { describe, expect, it } from "vitest";
import {
  resolveDropTarget,
  isOverRows,
  type Rect,
  type RowBox,
} from "@/utils/dropGeometry";

const rect = (left: number, top: number, right: number, bottom: number): Rect => ({
  left,
  top,
  right,
  bottom,
});

/**
 * Two rows, 100px tall each with a 20px gap. Row 0 is a single full-width
 * column holding two stacked fields; row 1 is two columns side by side.
 *
 *   x:  0        200       400
 *   y:0   ┌──────────────────┐
 *         │ row 0  cell 0    │
 *     50  │        cell 1    │
 *    100  └──────────────────┘
 *    120  ┌────────┬─────────┐
 *         │ col 0  │  col 1  │
 *    220  └────────┴─────────┘
 */
const layout = (): RowBox[] => [
  {
    rowIndex: 0,
    rect: rect(0, 0, 400, 100),
    columns: [
      {
        columnIndex: 0,
        rect: rect(0, 0, 400, 100),
        cells: [
          { cellIndex: 0, rect: rect(0, 0, 400, 50) },
          { cellIndex: 1, rect: rect(0, 50, 400, 100) },
        ],
      },
    ],
  },
  {
    rowIndex: 1,
    rect: rect(0, 120, 400, 220),
    columns: [
      { columnIndex: 0, rect: rect(0, 120, 200, 220), cells: [{ cellIndex: 0, rect: rect(0, 120, 200, 220) }] },
      { columnIndex: 1, rect: rect(200, 120, 400, 220), cells: [{ cellIndex: 0, rect: rect(200, 120, 400, 220) }] },
    ],
  },
];

describe("an empty canvas", () => {
  it("has nowhere to drop", () => {
    expect(resolveDropTarget([], 10, 10)).toBeNull();
  });
});

describe("dropping outside the rows", () => {
  it("above everything starts a new first row", () => {
    const target = resolveDropTarget(layout(), 200, -30)!;
    expect(target).toMatchObject({ kind: "row", rowIndex: 0 });
  });

  it("just below the last row appends a new row", () => {
    const target = resolveDropTarget(layout(), 200, 260)!;
    expect(target).toMatchObject({ kind: "row", rowIndex: 2 });
  });

  it("far below the form is not a drop at all", () => {
    expect(resolveDropTarget(layout(), 200, 900)).toBeNull();
  });
});

describe("the edge band of a row", () => {
  /**
   * Rows sit flush against each other, so without a band the only way to make
   * a new row would be to hit the hairline between two of them.
   */
  it("near the top of a row means a new row above it", () => {
    const target = resolveDropTarget(layout(), 200, 5)!;
    expect(target).toMatchObject({ kind: "row", rowIndex: 0 });
  });

  it("near the bottom of a row means a new row below it", () => {
    const target = resolveDropTarget(layout(), 200, 214)!;
    expect(target).toMatchObject({ kind: "row", rowIndex: 2 });
  });

  /**
   * The catchment must not eat the top of the first field, or there is no way
   * to stack something above it -- every drop there becomes a new row.
   */
  it("leaves room to stack above the first field in a row", () => {
    expect(resolveDropTarget(layout(), 200, 20)).toMatchObject({
      kind: "cell",
      cellIndex: 0,
    });
  });

  it("the middle of a row drops into the row, not beside it", () => {
    expect(resolveDropTarget(layout(), 200, 50)!.kind).not.toBe("row");
  });
});

describe("across the columns of a row", () => {
  it("near the left edge of a column makes a column before it", () => {
    const target = resolveDropTarget(layout(), 205, 170)!;
    expect(target).toMatchObject({ kind: "column", rowIndex: 1, columnIndex: 1 });
  });

  it("near the right edge of the last column appends a column", () => {
    const target = resolveDropTarget(layout(), 395, 170)!;
    expect(target).toMatchObject({ kind: "column", rowIndex: 1, columnIndex: 2 });
  });

  it("past the right of the row appends a column", () => {
    const target = resolveDropTarget(layout(), 480, 170)!;
    expect(target).toMatchObject({ kind: "column", rowIndex: 1, columnIndex: 2 });
  });

  it("the middle of a column drops into it rather than beside it", () => {
    const target = resolveDropTarget(layout(), 100, 170)!;
    expect(target).toMatchObject({ kind: "cell", rowIndex: 1, columnIndex: 0 });
  });
});

describe("stacking inside a column", () => {
  it("above the midpoint of the first field goes before it", () => {
    const target = resolveDropTarget(layout(), 200, 20)!;
    expect(target).toMatchObject({ kind: "cell", cellIndex: 0 });
  });

  it("between the two fields goes between them", () => {
    expect(resolveDropTarget(layout(), 200, 60)).toMatchObject({
      kind: "cell",
      cellIndex: 1,
    });
  });

  it("below the midpoint of the first field goes between the two", () => {
    const target = resolveDropTarget(layout(), 200, 40)!;
    expect(target).toMatchObject({ kind: "cell", cellIndex: 1 });
  });

  it("below the last field goes to the end", () => {
    const target = resolveDropTarget(layout(), 200, 85)!;
    expect(target).toMatchObject({ kind: "cell", cellIndex: 2 });
  });
});

describe("the indicator", () => {
  it("is a horizontal line spanning the row when making a row", () => {
    const { indicator } = resolveDropTarget(layout(), 200, 5)!;
    expect(indicator.orientation).toBe("horizontal");
    expect(indicator.length).toBe(400);
  });

  it("sits in the gap between the rows it would separate", () => {
    // Near the top of row 1, so the line goes in the gap above it: row 0 ends
    // at 100 and row 1 starts at 120.
    const { indicator } = resolveDropTarget(layout(), 200, 125)!;
    expect(indicator.top).toBe(110);
  });

  it("is a vertical line spanning the row height when making a column", () => {
    const { indicator } = resolveDropTarget(layout(), 205, 170)!;
    expect(indicator.orientation).toBe("vertical");
    expect(indicator.length).toBe(100);
    expect(indicator.left).toBe(200);
  });

  it("spans only the column when stacking inside one", () => {
    const { indicator } = resolveDropTarget(layout(), 100, 170)!;
    expect(indicator.orientation).toBe("horizontal");
    expect(indicator.length).toBe(200);
  });
});

describe("knowing whether the pointer is over the form", () => {
  it("is true inside a row and false in the margin", () => {
    expect(isOverRows(layout(), 200, 50)).toBe(true);
    expect(isOverRows(layout(), 200, 110)).toBe(false);
    expect(isOverRows(layout(), 900, 50)).toBe(false);
  });
});
