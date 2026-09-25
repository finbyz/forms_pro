/**
 * Google reCAPTCHA v3 — invisible, score-based.
 *
 * The script is loaded lazily the first time a token is needed, so forms with
 * CAPTCHA switched off never pull in Google's script at all.
 */

declare global {
  interface Window {
    grecaptcha?: {
      ready: (cb: () => void) => void;
      execute: (siteKey: string, opts: { action: string }) => Promise<string>;
    };
  }
}

const SCRIPT_ID = "forms-pro-recaptcha";

let loaderPromise: Promise<void> | null = null;
let loadedSiteKey: string | null = null;

function loadScript(siteKey: string): Promise<void> {
  // The v3 script is bound to one site key, so a different key needs a reload.
  if (loaderPromise && loadedSiteKey === siteKey) return loaderPromise;

  loadedSiteKey = siteKey;
  loaderPromise = new Promise<void>((resolve, reject) => {
    const existing = document.getElementById(SCRIPT_ID);
    if (existing) existing.remove();

    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(siteKey)}`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loaderPromise = null;
      loadedSiteKey = null;
      reject(new Error("Could not load reCAPTCHA"));
    };
    document.head.appendChild(script);
  });

  return loaderPromise;
}

/**
 * Mint a reCAPTCHA token for `action`.
 *
 * Returns null when no site key is configured — the caller submits without a
 * token and the server decides whether that is acceptable. Never swallow a
 * failure into a silent success here: if CAPTCHA is required server-side, the
 * submission is rejected there rather than being waved through.
 */
export async function getRecaptchaToken(
  siteKey: string | null | undefined,
  action = "submit"
): Promise<string | null> {
  if (!siteKey) return null;

  await loadScript(siteKey);

  const grecaptcha = window.grecaptcha;
  if (!grecaptcha) throw new Error("reCAPTCHA failed to initialise");

  await new Promise<void>((resolve) => grecaptcha.ready(() => resolve()));
  return grecaptcha.execute(siteKey, { action });
}

/** Preload the script so the first submit isn't waiting on a network round trip. */
export function warmRecaptcha(siteKey: string | null | undefined): void {
  if (!siteKey) return;
  loadScript(siteKey).catch(() => {
    /* the submit path reports the failure */
  });
}
