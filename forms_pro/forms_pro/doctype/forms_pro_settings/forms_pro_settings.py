import frappe
from frappe.model.document import Document


class FormsProSettings(Document):
    def validate(self):
        if self.require_captcha_for_public_forms:
            if not self.recaptcha_site_key or not self.recaptcha_secret_key:
                frappe.msgprint(
                    "CAPTCHA is enabled but site key or secret key is missing.",
                    alert=True,
                    indicator="orange",
                )

    def on_update(self):
        frappe.cache.delete_keys("forms_pro_settings:*")
        if hasattr(frappe, "cache"):
            frappe.cache.delete_key("forms_pro_settings:main")