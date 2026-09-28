import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { Fieldtype } from "@/types/FormsPro/form_field.types";

/**
 * The palette groups field types by hand-written category. A type that no
 * category claimed was dropped from the list with no error anywhere — it was
 * registered, typechecked, shipped, and still impossible to add to a form.
 * That is how the Language field went missing.
 *
 * These mirror AddFieldsSection's categories. Checked against the Fieldtype
 * enum rather than the component registry, because the enum is plain TS while
 * the registry pulls in .vue files that this test runner cannot parse.
 */
const CATEGORISED: string[] = [
  Fieldtype.DATA,
  Fieldtype.NUMBER,
  Fieldtype.CURRENCY,
  Fieldtype.EMAIL,
  Fieldtype.PHONE,
  Fieldtype.URL,
  Fieldtype.TEXTAREA,
  Fieldtype.TEXT_EDITOR,
  Fieldtype.SELECT,
  Fieldtype.MULTISELECT,
  Fieldtype.CHECKBOX,
  Fieldtype.SWITCH,
  Fieldtype.RATING,
  Fieldtype.LANGUAGE,
  Fieldtype.DATE,
  Fieldtype.DATE_TIME,
  Fieldtype.DATE_RANGE,
  Fieldtype.TIME_PICKER,
  Fieldtype.ATTACH,
  Fieldtype.HEADING_1,
  Fieldtype.HEADING_2,
  Fieldtype.HEADING_3,
  Fieldtype.LINK,
  Fieldtype.PASSWORD,
  Fieldtype.TABLE,
];

/** Added through the step controls, never dragged from the palette. */
const NOT_IN_PALETTE = new Set<string>([Fieldtype.PAGE_BREAK]);

describe("field palette coverage", () => {
  it("offers the Language field", () => {
    expect(CATEGORISED).toContain(Fieldtype.LANGUAGE);
  });

  it("every field type is reachable from the palette", () => {
    const missing = Object.values(Fieldtype)
      .filter((name) => !NOT_IN_PALETTE.has(name))
      .filter((name) => !CATEGORISED.includes(name));

    expect(missing, `uncategorised field types: ${missing.join(", ")}`).toEqual([]);
  });

  it("names no field type that does not exist", () => {
    const known = new Set<string>(Object.values(Fieldtype));
    const stale = CATEGORISED.filter((name) => !known.has(name));

    expect(stale, `categorised but unknown: ${stale.join(", ")}`).toEqual([]);
  });
});

/**
 * The palette lists a field type only if the component registry has an entry
 * for it. Currency was added to the enum and to a palette category but never
 * to the registry, so it was invisible in the builder while these tests still
 * passed -- they only ever compared the enum to the categories.
 *
 * Read as text rather than imported: the registry pulls in .vue files, which
 * this runner has no plugin for.
 */
describe("field type registry", () => {
  const registrySource = readFileSync(
    fileURLToPath(new URL("../config/fieldTypes.ts", import.meta.url)),
    "utf8"
  );

  it("registers a component for every field type", () => {
    const unregistered = Object.keys(Fieldtype).filter(
      (key) => !registrySource.includes(`name: Fieldtype.${key},`)
    );

    expect(
      unregistered,
      `field types with no registry entry: ${unregistered.join(", ")}`
    ).toEqual([]);
  });
});
