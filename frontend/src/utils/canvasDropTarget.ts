/**
 * Reading the canvas layout out of the DOM, so the geometry can decide.
 *
 * Kept apart from `dropGeometry` on purpose: the rules there are pure and
 * testable, and this is the thin part that measures. The canvas already tags
 * every row, column and card with data attributes for exactly this sort of
 * lookup, so nothing here needs Vue state -- it reads what is on screen at the
 * moment the pointer moved.
 */

import type { ColumnBox, Rect, RowBox } from "@/utils/dropGeometry";

const ROW_SELECTOR = '[data-form-builder-component="form-row"]';
const COLUMN_SELECTOR = '[data-form-builder-component="cell-column"]';
const CARD_SELECTOR = '[data-form-builder-component="field-card"]';

/** What a drag is carrying, written on dragstart and read on drop. */
export const DRAG_PAYLOAD_TYPE = "application/x-forms-pro-field";

export type DragPayload =
  | { source: "canvas"; fieldname: string }
  | { source: "palette"; fieldtype: string }
  | { source: "doctype"; fieldname: string };

function toRect(element: Element): Rect {
  const { left, top, right, bottom } = element.getBoundingClientRect();
  return { left, top, right, bottom };
}

function readIndex(element: Element, attribute: string, fallback: number): number {
  const raw = element.getAttribute(attribute);
  const value = raw === null ? Number.NaN : Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

/**
 * Measure the rows currently on the canvas.
 *
 * The dragged card is left out: a field cannot be a landmark for deciding
 * where it should go, and including it makes the indicator jump to wherever
 * the field already is.
 */
export function readRows(canvas: HTMLElement, draggedFieldname?: string): RowBox[] {
  const rows: RowBox[] = [];

  canvas.querySelectorAll(ROW_SELECTOR).forEach((rowEl, rowPosition) => {
    const columns: ColumnBox[] = [];

    rowEl.querySelectorAll(COLUMN_SELECTOR).forEach((columnEl, columnPosition) => {
      const cells = Array.from(columnEl.querySelectorAll(CARD_SELECTOR))
        .filter((card) => card.getAttribute("data-field-name") !== draggedFieldname)
        .map((card, cellPosition) => ({
          cellIndex: readIndex(card, "data-cell-index", cellPosition),
          rect: toRect(card),
        }));

      columns.push({
        columnIndex: readIndex(columnEl, "data-col-index", columnPosition),
        rect: toRect(columnEl),
        cells,
      });
    });

    rows.push({
      rowIndex: readIndex(rowEl, "data-row-index", rowPosition),
      rect: toRect(rowEl),
      columns,
    });
  });

  return rows;
}

export function writeDragPayload(event: DragEvent, payload: DragPayload): void {
  if (!event.dataTransfer) return;
  event.dataTransfer.effectAllowed = payload.source === "canvas" ? "move" : "copy";
  event.dataTransfer.setData(DRAG_PAYLOAD_TYPE, JSON.stringify(payload));
  // Firefox refuses to start a drag unless some standard type is set too.
  event.dataTransfer.setData("text/plain", " ");
}

export function readDragPayload(event: DragEvent): DragPayload | null {
  const raw = event.dataTransfer?.getData(DRAG_PAYLOAD_TYPE);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as DragPayload;
  } catch {
    return null;
  }
}
