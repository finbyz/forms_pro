"""Embed script serving for Forms Pro public forms."""
from __future__ import annotations

import frappe


EMBED_JS = """(function() {
  var scripts = document.getElementsByTagName('script');
  var me = scripts[scripts.length - 1];
  var container = document.querySelector('[data-forms-pro="' + me.getAttribute('data-route') + '"]');
  if (!container) return;

  var iframe = document.createElement('iframe');
  iframe.src = me.getAttribute('data-base') + '/forms/p/' + me.getAttribute('data-route') + '?embed=1';
  iframe.style.width = '100%';
  iframe.style.border = 'none';
  iframe.style.overflow = 'hidden';
  iframe.setAttribute('scrolling', 'no');
  container.appendChild(iframe);

  iframe.onload = function() {
    window.addEventListener('message', function(e) {
      if (e.data && e.data.source === 'forms-pro') {
        if (e.data.event === 'formspro:resize') {
          iframe.style.height = e.data.height + 'px';
        }
        if (e.data.event === 'formspro:submitted') {
          window.dispatchEvent(new CustomEvent('forms-pro-submitted', { detail: e.data }));
          if (window.dataLayer) {
            window.dataLayer.push({ event: 'formspro_form_submit', form_name: e.data.form, submission_id: e.data.submission_id });
          }
        }
      }
    });
  };
})();"""


@frappe.whitelist(allow_guest=True)
def get_embed_script():
    """Serve the embed JavaScript."""
    frappe.response.type = "javascript"
    frappe.response.headers["Cache-Control"] = "public, max-age=3600"
    return EMBED_JS