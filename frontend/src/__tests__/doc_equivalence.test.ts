import { describe, expect, it } from "vitest";
import { sameDoc } from "@/utils/doc_equivalence";

/**
 * A freshly saved form must not look unsaved. Every one of these pairs is the
 * saved copy against what a control handed back -- and each used to start a
 * save the server treated as identical, round and round.
 */
describe("whether the form really changed", () => {
  it("ignores a checkbox handed back as a boolean", () => {
    expect(sameDoc({ allow_incomplete: 1 }, { allow_incomplete: true })).toBe(true);
    expect(sameDoc({ reqd: 0 }, { reqd: false })).toBe(true);
  });

  it("ignores empty values in a different shape", () => {
    expect(sameDoc({ description: null }, { description: "" })).toBe(true);
    expect(sameDoc({ default: undefined }, { default: null })).toBe(true);
  });

  it("ignores numbers handed back as text", () => {
    expect(sameDoc({ max_length: 140 }, { max_length: "140" })).toBe(true);
  });

  it("ignores the server's rewrite of inline styles", () => {
    expect(
      sameDoc(
        { description: '<p style="text-align: center">x</p>' },
        { description: '<p style="text-align:center">x</p>' }
      )
    ).toBe(true);
  });

  it("ignores bookkeeping the server stamps on every save", () => {
    expect(sameDoc({ title: "A", modified: "t1" }, { title: "A", modified: "t2" })).toBe(true);
  });

  it("looks inside child rows", () => {
    expect(sameDoc({ fields: [{ reqd: 1 }] }, { fields: [{ reqd: true }] })).toBe(true);
    expect(sameDoc({ fields: [{ reqd: 1 }] }, { fields: [{ reqd: 0 }] })).toBe(false);
  });

  it("still sees every real edit", () => {
    expect(sameDoc({ allow_incomplete: 1 }, { allow_incomplete: false })).toBe(false);
    expect(sameDoc({ title: "A" }, { title: "B" })).toBe(false);
    expect(sameDoc({ description: "" }, { description: "<p>x</p>" })).toBe(false);
    expect(sameDoc({ fields: [{}] }, { fields: [{}, {}] })).toBe(false);
  });
});
