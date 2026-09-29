/**
 * Where a dragged field would land, worked out from rectangles and a pointer.
 *
 * The builder used to answer this by letting SortableJS physically move DOM
 * nodes as the pointer passed over them -- roughly a hundred Sortable
 * instances, one per column and one per gap, each mutating the document on
 * every pointer move and re-triggering Vue's row grouping. That is what made
 * the canvas stutter, and no amount of tuning fixes it, because the work is
 * the design.
 *
 * Frappe Studio's canvas (frontend/src/utils/dropGeometry.ts there) takes the
 * other approach, and so does this: nothing in the canvas moves during a drag.
 * The pointer is read against a snapshot of the current layout, a single line
 * is drawn where the field would go, and the form is only changed on drop.
 *
 * Everything here is pure -- rects in, a decision out -- so the rules can be
 * tested without a browser. All coordinates are client (viewport) space, which
 * is what `getBoundingClientRect` gives and what a fixed overlay needs.
 */

export interface Rect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/** A column of stacked fields inside a row. */
export interface ColumnBox {
  columnIndex: number;
  rect: Rect;
  /** The fields stacked in this column, top to bottom. */
  cells: { cellIndex: number; rect: Rect }[];
}

/** One row of the form, holding one or more columns side by side. */
export interface RowBox {
  rowIndex: number;
  rect: Rect;
  columns: ColumnBox[];
}

/**
 * Only two outcomes. A drag either puts the field on its own new row, or
 * places it inside a column that already exists. It cannot create a column --
 * that is the split control's job.
 */
export type DropKind = "row" | "cell";

export interface DropTarget {
  kind: DropKind;
  /** Row to insert at, or the row being inserted into. */
  rowIndex: number;
  /** Set for "cell". */
  columnIndex?: number;
  /** Set for "cell": the position within the column. */
  cellIndex?: number;
  /** The line to draw, in client coordinates. */
  indicator: Indicator;
}

/**
 * The line to draw. Always horizontal: a drag either inserts a row or stacks
 * into a column, and both of those are a gap between things above and below.
 */
export interface Indicator {
  left: number;
  top: number;
  length: number;
}

/**
 * How far into a row the gap above or below it still counts as "make a new
 * row". The rows are laid out with a real gap between them, but a gap is a
 * small target, so its catchment reaches a little way into the rows either
 * side.
 *
 * Fixed pixels, not a fraction of the row. A fraction sounds tidier and is
 * wrong: on a row holding two stacked fields, 28% of the height swallows the
 * whole top half of the first field, so "stack above this field" becomes
 * unreachable and every drop there turns into a new row instead. The unit
 * tests caught exactly that.
 */
const GAP_CATCH = 12;

/** A drop this far below the last row lands at the end rather than nowhere. */
const TRAILING_SLACK = 160;

const height = (r: Rect) => r.bottom - r.top;
const width = (r: Rect) => r.right - r.left;

function horizontal(rect: Rect, y: number): Indicator {
  return { left: rect.left, top: y, length: width(rect) };
}

/** The gap between two edges, or the edge itself when there is nothing opposite. */
function midpoint(before: number | null, after: number | null): number {
  if (before === null) return after as number;
  if (after === null) return before;
  return (before + after) / 2;
}

function newRowTarget(rows: RowBox[], rowIndex: number): DropTarget {
  const above = rows[rowIndex - 1];
  const below = rows[rowIndex];
  const reference = below?.rect ?? above?.rect;
  const y = midpoint(above ? above.rect.bottom : null, below ? below.rect.top : null);
  return {
    kind: "row",
    rowIndex,
    indicator: horizontal(reference, y),
  };
}

function cellTarget(row: RowBox, column: ColumnBox, cellIndex: number): DropTarget {
  const before = column.cells[cellIndex - 1];
  const after = column.cells[cellIndex];
  const y = midpoint(before ? before.rect.bottom : null, after ? after.rect.top : null);
  return {
    kind: "cell",
    rowIndex: row.rowIndex,
    columnIndex: column.columnIndex,
    cellIndex,
    indicator: horizontal(column.rect, y),
  };
}

function contains(rect: Rect, x: number, y: number): boolean {
  return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
}

/**
 * Resolve the pointer to a drop target.
 *
 * Reads outside in: which row, then whether the pointer is near that row's top
 * or bottom edge (a new row) or inside it, and finally which existing column
 * it is over and which gap between that column's fields it is nearest.
 *
 * Dragging never splits a row into columns. It used to: brushing past the side
 * of a field turned the row into two columns, so an ordinary drag up or down
 * kept producing side-by-side layouts nobody asked for. Columns are made
 * deliberately, with the split control on the field, and dragging then moves
 * fields into the columns that exist.
 *
 * Returns null only when there is no layout to drop into at all, which the
 * caller renders as "drop to start the form".
 */
export function resolveDropTarget(
  rows: RowBox[],
  x: number,
  y: number
): DropTarget | null {
  if (!rows.length) return null;

  const first = rows[0];
  const last = rows[rows.length - 1];

  // Above everything, or below everything but still near the form.
  if (y < first.rect.top) return newRowTarget(rows, 0);
  if (y > last.rect.bottom) {
    return y - last.rect.bottom > TRAILING_SLACK ? null : newRowTarget(rows, rows.length);
  }

  const row =
    rows.find((r) => y >= r.rect.top && y <= r.rect.bottom) ??
    // Between two rows: belongs to whichever starts next.
    rows.find((r) => r.rect.top > y) ??
    last;

  // Never more than a third of a short row, or a row barely taller than the
  // catchment would accept nothing but new rows.
  const catchment = Math.min(GAP_CATCH, height(row.rect) / 3);
  if (y < row.rect.top + catchment) return newRowTarget(rows, row.rowIndex);
  if (y > row.rect.bottom - catchment) return newRowTarget(rows, row.rowIndex + 1);

  // A row with no columns has nothing to drop into, so this becomes a new row.
  if (!row.columns.length) return newRowTarget(rows, row.rowIndex);

  // Horizontal position only chooses which existing column, never makes one.
  const column = nearestColumn(row, x);

  if (!column.cells.length) return cellTarget(row, column, 0);

  for (const cell of column.cells) {
    const middle = cell.rect.top + height(cell.rect) / 2;
    if (y < middle) return cellTarget(row, column, cell.cellIndex);
  }
  return cellTarget(row, column, column.cells.length);
}

/** The column the pointer is over, or the closest one when it is past the ends. */
function nearestColumn(row: RowBox, x: number): ColumnBox {
  const inside = row.columns.find((c) => x >= c.rect.left && x <= c.rect.right);
  if (inside) return inside;

  return row.columns.reduce((closest, candidate) => {
    const distance = Math.min(
      Math.abs(x - candidate.rect.left),
      Math.abs(x - candidate.rect.right)
    );
    const best = Math.min(
      Math.abs(x - closest.rect.left),
      Math.abs(x - closest.rect.right)
    );
    return distance < best ? candidate : closest;
  });
}

/** True when the pointer is inside the area the form occupies. */
export function isOverRows(rows: RowBox[], x: number, y: number): boolean {
  return rows.some((row) => contains(row.rect, x, y));
}
