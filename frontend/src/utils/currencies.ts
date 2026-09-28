/**
 * Currency utilities for Forms Pro.
 * Provides symbols, formatting, and options mirroring Frappe Desk conventions.
 */

export const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  INR: "₹",
  CHF: "CHF",
  SEK: "kr",
  NOK: "kr",
  DKK: "kr",
  CAD: "$",
  AUD: "$",
  NZD: "$",
  JPY: "¥",
  CNY: "¥",
  SGD: "$",
  HKD: "$",
  AED: "د.إ",
  SAR: "﷼",
  BRL: "R$",
  ZAR: "R",
  MXN: "$",
  PLN: "zł",
  RUB: "₽",
  TRY: "₺",
  KRW: "₩",
};

export const COMMON_CURRENCY_OPTIONS = [
  { label: "Default (System Currency)", value: "" },
  { label: "USD - US Dollar ($)", value: "USD" },
  { label: "EUR - Euro (€)", value: "EUR" },
  { label: "CHF - Swiss Franc (CHF)", value: "CHF" },
  { label: "SEK - Swedish Krona (kr)", value: "SEK" },
  { label: "GBP - British Pound (£)", value: "GBP" },
  { label: "INR - Indian Rupee (₹)", value: "INR" },
  { label: "CAD - Canadian Dollar ($)", value: "CAD" },
  { label: "AUD - Australian Dollar ($)", value: "AUD" },
  { label: "JPY - Japanese Yen (¥)", value: "JPY" },
  { label: "CNY - Chinese Yuan (¥)", value: "CNY" },
  { label: "SGD - Singapore Dollar ($)", value: "SGD" },
  { label: "AED - UAE Dirham (د.إ)", value: "AED" },
  { label: "SAR - Saudi Riyal (﷼)", value: "SAR" },
  { label: "NOK - Norwegian Krone (kr)", value: "NOK" },
  { label: "DKK - Danish Krone (kr)", value: "DKK" },
  { label: "BRL - Brazilian Real (R$)", value: "BRL" },
  { label: "ZAR - South African Rand (R)", value: "ZAR" },
  { label: "PLN - Polish Zloty (zł)", value: "PLN" },
  { label: "TRY - Turkish Lira (₺)", value: "TRY" },
];

/**
 * Returns the symbol for a given currency code.
 * Falls back to Frappe sysdefaults, or "$".
 */
export function getCurrencySymbol(currency?: string | null): string {
  const code = (currency || (window as any).frappe?.boot?.sysdefaults?.currency || "USD").trim().toUpperCase();
  return CURRENCY_SYMBOLS[code] || code || "$";
}

/**
 * Formats a number or numeric string with thousand separators and optional decimal precision.
 * e.g. 989088 -> "989,088.00"
 */
export function formatCurrencyAmount(value: string | number | null | undefined, precision = 2): string {
  if (value === null || value === undefined || value === "") return "";
  const cleaned = String(value).replace(/,/g, "").trim();
  const num = Number(cleaned);
  if (Number.isNaN(num)) return String(value);

  // If input already has decimal parts, respect precision
  return num.toLocaleString("en-US", {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  });
}

/**
 * Cleans user input into a plain numeric string for storage/submission.
 */
export function cleanCurrencyInput(value: string | null | undefined): string {
  if (!value) return "";
  return String(value).replace(/,/g, "").trim();
}
