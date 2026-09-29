/**
 * Whether two pieces of rich text are the same content.
 *
 * The editor and the server disagree about how to *write* the same thing.
 * Frappe's HTML sanitiser rewrites inline styles when a Text Editor value is
 * saved -- `text-align: center` comes back as `text-align:center`, and
 * `rgb(255,0,0)` as `rgb(255, 0, 0)` -- while the editor always serialises
 * its own way. Compared as strings, every save looked like a fresh edit: the
 * server's version went into the editor, the editor wrote its version back,
 * that was saved and rewritten again, and the header flipped between
 * "Saving..." and "Unsaved" for as long as the page was open. A centred
 * heading was enough to start it.
 *
 * Comparing the canonical form ignores those rewrites and nothing else.
 */
export function canonicalHtml(html: string | null | undefined): string {
  if (!html) return "";
  const trimmed = html
    .replace(/style="([^"]*)"/g, (_, css: string) => `style="${css.replace(/\s+/g, "")}"`)
    .trim();
  // An empty editor serialises as an empty paragraph.
  return trimmed === "<p></p>" ? "" : trimmed;
}

export function sameHtml(
  a: string | null | undefined,
  b: string | null | undefined
): boolean {
  return canonicalHtml(a) === canonicalHtml(b);
}
