/**
 * Fold a save's response into the form being edited, instead of replacing it.
 *
 * frappe-ui answers a successful save by swapping in the server's copy of the
 * document wholesale. The builder cannot live with that: the field properties
 * panel holds the selected field *object*, so after the first autosave it was
 * editing a row that was no longer part of the form. Options typed into a
 * Select, a condition added to a field -- none of it was saved or published
 * until the field happened to be clicked again. And anything typed while the
 * save was on its way was overwritten by the response.
 *
 * So the edited document keeps its identity, and only what the author has not
 * touched since the save was sent takes the server's value: the timestamp, the
 * names given to new rows, the mapping the server fills in. Whatever the author
 * changed while the save was in flight is kept, and saved next.
 */
import { canonicalDoc } from "@/utils/doc_equivalence";

type Row = Record<string, any>;

function same(a: unknown, b: unknown): boolean {
  return canonicalDoc(a) === canonicalDoc(b);
}

/** Take the server's value wherever the local value is still what was sent. */
function adoptUntouched(local: Row, sent: Row, server: Row, skip?: Set<string>) {
  const keys = new Set([...Object.keys(server), ...Object.keys(local)]);
  for (const key of keys) {
    if (skip?.has(key)) continue;
    if (!(key in server)) continue;
    if (same(local[key], sent?.[key])) local[key] = server[key];
  }
}

/**
 * @param live      the document object being edited (mutated in place)
 * @param sent      a plain copy of `live` taken when the save was sent
 * @param sentRows  the field row objects of `live` when the save was sent
 * @param server    the document the save returned
 */
export function mergeSavedDoc(live: Row, sent: Row, sentRows: Row[], server: Row): void {
  adoptUntouched(live, sent, server, new Set(["fields"]));

  const serverRows: Row[] = server.fields || [];
  const sentCopies: Row[] = sent.fields || [];
  const byName = new Map(serverRows.filter((r) => r.name).map((r) => [r.name, r]));
  const byFieldname = new Map(serverRows.map((r) => [r.fieldname, r]));
  const matched = new Set<Row>();

  sentRows.forEach((row, i) => {
    const copy = sentCopies[i];
    if (!copy) return;
    const serverRow =
      (copy.name && byName.get(copy.name)) || byFieldname.get(copy.fieldname);
    if (!serverRow) return;
    matched.add(serverRow);
    adoptUntouched(row, copy, serverRow);
  });

  // A row only the server knows about: added on save. Kept, unless the author
  // has rearranged the fields since -- then their order wins.
  const liveRows: Row[] = live.fields || [];
  const unchangedOrder =
    liveRows.length === sentRows.length && liveRows.every((row, i) => row === sentRows[i]);
  if (unchangedOrder) {
    for (const serverRow of serverRows) {
      if (!matched.has(serverRow)) liveRows.push(serverRow);
    }
  }
}
