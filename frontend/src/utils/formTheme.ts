/**
 * Form theming.
 *
 * Two rules learned the hard way:
 *
 *  1. Never style fields with a CSS fallback like `inherit`. When a token is
 *     unset, `border-radius: inherit` takes the parent's 0 and `border-color:
 *     inherit` takes black, which silently destroys frappe-ui's own styling.
 *     Instead the themed class is only applied when a *complete* token set
 *     exists, so every `var()` inside it always resolves.
 *
 *  2. A font that is not loaded changes nothing. Picking "Poppins" has no
 *     visible effect unless the stylesheet is fetched first.
 */

export type ThemeTokens = {
  font_family: string;
  font_size: string;
  text_color: string;
  muted_text_color: string;
  background_color: string;
  primary_color: string;
  primary_hover_color: string;
  input_border_color: string;
  input_focus_color: string;
  input_radius: string;
  button_radius: string;
  card_radius: string;
  form_max_width: string;
  field_gap: string;
};

/** Must stay in step with ThemeEditor's defaults. */
export const THEME_DEFAULTS: ThemeTokens = {
  font_family: "Inter",
  font_size: "16px",
  text_color: "#111827",
  muted_text_color: "#6B7280",
  background_color: "#FFFFFF",
  primary_color: "#1D4ED8",
  primary_hover_color: "#1E40AF",
  input_border_color: "#D1D5DB",
  input_focus_color: "#2563EB",
  input_radius: "8px",
  button_radius: "8px",
  card_radius: "12px",
  form_max_width: "720px",
  field_gap: "16px",
};

const TOKEN_TO_VAR: Record<keyof ThemeTokens, string> = {
  font_family: "--fp-font-family",
  font_size: "--fp-font-size",
  text_color: "--fp-text-color",
  muted_text_color: "--fp-muted-text-color",
  background_color: "--fp-background-color",
  primary_color: "--fp-primary-color",
  primary_hover_color: "--fp-primary-hover-color",
  input_border_color: "--fp-input-border-color",
  input_focus_color: "--fp-input-focus-color",
  input_radius: "--fp-input-radius",
  button_radius: "--fp-button-radius",
  card_radius: "--fp-card-radius",
  form_max_width: "--fp-form-max-width",
  field_gap: "--fp-field-gap",
};

/** Colours, lengths and font stacks only — these end up in a style attribute. */
const SAFE_VALUE = /^[#a-zA-Z0-9\s,.()%'"-]+$/;

/** Fonts available in the Design tab, all served by Google Fonts. */
const WEB_FONTS = new Set([
  "Roboto",
  "Open Sans",
  "Poppins",
  "Montserrat",
  "Nunito",
  "Source Sans Pro",
  "Lato",
  "Work Sans",
]);

export function parseTheme(raw: unknown): Partial<ThemeTokens> {
  if (!raw) return {};
  if (typeof raw === "object") return raw as Partial<ThemeTokens>;
  try {
    const parsed = JSON.parse(String(raw));
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

/** True when the form carries any theme at all. */
export function hasTheme(raw: unknown): boolean {
  return Object.keys(parseTheme(raw)).length > 0;
}

/**
 * Load a Google Font once. Without this, choosing a font in the Design tab
 * changes the CSS but the browser falls back and nothing looks different.
 */
export function ensureFontLoaded(family: string | undefined): void {
  if (!family || !WEB_FONTS.has(family)) return; // Inter is already bundled

  const id = `fp-font-${family.replace(/\s+/g, "-").toLowerCase()}`;
  if (document.getElementById(id)) return;

  const link = document.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(
    family
  )}:wght@400;500;600;700&display=swap`;
  document.head.appendChild(link);
}

/**
 * Apply a theme to an element.
 *
 * Tokens are merged over the defaults so the set is always complete, and the
 * `fp-themed` class is only added when the form actually has a theme — that is
 * what keeps an unthemed form on frappe-ui's own styling.
 */
export function applyTheme(el: HTMLElement | null, raw: unknown): void {
  if (!el) return;

  const overrides = parseTheme(raw);

  if (!Object.keys(overrides).length) {
    el.classList.remove("fp-themed");
    for (const cssVar of Object.values(TOKEN_TO_VAR)) el.style.removeProperty(cssVar);
    return;
  }

  const tokens: ThemeTokens = { ...THEME_DEFAULTS, ...overrides };
  ensureFontLoaded(tokens.font_family);

  for (const [token, cssVar] of Object.entries(TOKEN_TO_VAR)) {
    const value = tokens[token as keyof ThemeTokens];
    if (typeof value === "string" && value.trim() && SAFE_VALUE.test(value)) {
      el.style.setProperty(cssVar, value.trim());
    } else {
      el.style.setProperty(cssVar, THEME_DEFAULTS[token as keyof ThemeTokens]);
    }
  }

  el.classList.add("fp-themed");
}
