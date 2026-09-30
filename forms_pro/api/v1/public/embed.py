"""Embed script serving for Forms Pro public forms."""
from __future__ import annotations

import frappe
from werkzeug.wrappers import Response


EMBED_JS = """(function() {
  // `currentScript` is the tag actually running. The old fallback of "the last
  // script on the page" is only correct for a synchronous tag -- with `async`
  // this script may not be last when it executes, and it would then read
  // another tag's attributes and never find its container.
  var scripts = document.getElementsByTagName('script');
  var me = document.currentScript || scripts[scripts.length - 1];
  if (!me) return;
  var route = me.getAttribute('data-route');
  if (!route) return;
  var container = document.querySelector('[data-forms-pro="' + route + '"]');
  if (!container) return;

  // Size comes from the snippet when given. Width and height used to be
  // hard-coded here, so editing them in the embed code changed nothing.
  var width = me.getAttribute('data-width') || '100%';
  var height = (me.getAttribute('data-height') || '').trim();
  // No height, or "auto", means the frame grows to fit the whole form.
  var fitToContent = !height || height === 'auto';

  var iframe = document.createElement('iframe');
  iframe.src = me.getAttribute('data-base') + '/forms/p/' + route + '?embed=1';
  iframe.style.width = width;
  iframe.style.border = 'none';

  // A frame must never cut the form off. With a fixed height it scrolls inside
  // itself; it used to have scrolling switched off in every case, so a snippet
  // with data-height="650px" showed the first 650px of the form and nothing
  // below it could be reached. When fitting to content, it scrolls only until
  // the form has reported its height -- if that never arrives, the visitor can
  // still reach the whole form.
  iframe.setAttribute('scrolling', 'auto');
  iframe.style.overflow = 'auto';
  iframe.style.height = fitToContent ? '600px' : height;
  container.appendChild(iframe);

  // Registered before the iframe can send anything. Waiting for `onload` meant
  // an early resize or submit message arrived with nobody listening.
  window.addEventListener('message', function(e) {
    if (e.source !== iframe.contentWindow) return;
    if (!e.data || e.data.source !== 'forms-pro') return;

    // An explicit height in the snippet wins; otherwise grow to fit, and stop
    // scrolling now the whole form fits.
    if (e.data.event === 'formspro:resize' && fitToContent && e.data.height) {
      iframe.style.height = e.data.height + 'px';
      iframe.setAttribute('scrolling', 'no');
      iframe.style.overflow = 'hidden';
    }

    if (e.data.event === 'formspro:submitted') {
      window.dispatchEvent(new CustomEvent('forms-pro-submitted', { detail: e.data }));
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({
        event: 'formspro_form_submit',
        form_name: e.data.form,
        form_route: e.data.route,
        submission_id: e.data.submission_id
      });
    }
  });
})();"""


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_embed_script():
    """
    Serve the embed loader as JavaScript.

    Returns a Response directly. Two earlier attempts did not work: setting
    `frappe.response["type"] = "javascript"` is not a type Frappe knows, so
    building the response raised a KeyError and the endpoint answered 500; and
    the "download" type still came back as `application/json`, which a browser
    refuses to run as a script. The API layer hands a Response object straight
    through, so the content type is ours to set.
    """
    return Response(
        EMBED_JS,
        mimetype="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )
