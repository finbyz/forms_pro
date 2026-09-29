import { describe, expect, it } from "vitest";
import { canonicalHtml, sameHtml } from "@/utils/html_equivalence";

describe("rich text equivalence", () => {
  it("treats Frappe's rewritten styles as the same content", () => {
    expect(
      sameHtml(
        '<h2 style="text-align: center">Centred</h2>',
        '<h2 style="text-align:center">Centred</h2>'
      )
    ).toBe(true);
    expect(
      sameHtml(
        '<span style="color: rgb(255,0,0)">red</span>',
        '<span style="color:rgb(255, 0, 0)">red</span>'
      )
    ).toBe(true);
  });

  it("treats an empty editor as empty", () => {
    expect(sameHtml("<p></p>", "")).toBe(true);
    expect(sameHtml(null, "<p></p>")).toBe(true);
  });

  it("still sees a real edit", () => {
    expect(sameHtml("<h1>Heading</h1>", "<h1>Heading</h1><p>more</p>")).toBe(false);
    expect(sameHtml("<p>one two</p>", "<p>one  two</p>")).toBe(false);
  });

  it("leaves whitespace in the text itself alone", () => {
    expect(canonicalHtml("<p>a b</p>")).toBe("<p>a b</p>");
  });
});
