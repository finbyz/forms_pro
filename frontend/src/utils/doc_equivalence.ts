/**
 * Whether the form in the builder really differs from what was last saved.
 *
 * frappe-ui answers that by comparing the two documents byte for byte, and
 * the builder cannot live with that answer. Controls hand values back in a
 * different shape from the one the server sends -- `false` for `0`, `""` for
 * `null`, a number as a string -- and the server rewrites rich text on the way
 * in. Each of those made a freshly saved form look unsaved, autosave sent it
 * again, the server stored exactly the same thing, the response was echoed
 * back in the other shape, and the header flipped between "Saving..." and
 * "Unsaved" every couple of seconds for as long as the tab stayed open.
 *
 * Compared in canonical form, only a real change of content counts.
 */
import { canonicalHtml } from "@/utils/html_equivalence";

/** Bookkeeping the server rewrites on every save; never a change by the author. */
const IGNORED_KEYS = new Set(["modified", "modified_by", "creation", "owner", "docstatus"]);

function canonicalValue(value: unknown): unknown {
  if (value === null || value === undefined || value === "") return "";
  if (value === true) return "1";
  if (value === false) return "0";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") {
    return value.trimStart().startsWith("<") ? canonicalHtml(value) : value;
  }
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(value as object).sort()) {
      if (IGNORED_KEYS.has(key) || key.startsWith("__")) continue;
      out[key] = canonicalValue((value as Record<string, unknown>)[key]);
    }
    return out;
  }
  return value;
}

export function canonicalDoc(doc: unknown): string {
  return JSON.stringify(canonicalValue(doc));
}

export function sameDoc(a: unknown, b: unknown): boolean {
  return canonicalDoc(a) === canonicalDoc(b);
}
