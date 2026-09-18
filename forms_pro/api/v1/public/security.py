import frappe
import requests

def verify_captcha(token):
    settings = frappe.get_doc("Forms Pro Settings")
    if not settings.require_captcha_for_public_forms:
        return True
        
    if not token:
        frappe.throw("CAPTCHA token is missing.", exc=frappe.PermissionError)
        
    secret_key = settings.get_password("recaptcha_secret_key")
    if not secret_key:
        # If no secret is configured, allow pass-through or fail closed depending on policy
        frappe.log_error("Forms Pro CAPTCHA secret key is not configured.", "Forms Pro Security")
        return True
        
    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": secret_key,
            "response": token,
            "remoteip": frappe.local.request_ip
        }
    )
    
    result = response.json()
    if not result.get("success"):
        frappe.throw("CAPTCHA verification failed.", exc=frappe.PermissionError)
        
    score = result.get("score", 0)
    threshold = settings.default_score_threshold or 0.5
    
    if score < threshold:
        frappe.throw("CAPTCHA score too low. Suspicious activity detected.", exc=frappe.PermissionError)
        
    return True

def check_rate_limit(route):
    # 10 requests per minute per IP per form
    ip = frappe.local.request_ip
    cache_key = f"forms_pro_rate_limit:{route}:{ip}"
    
    count = frappe.cache().get_value(cache_key) or 0
    if count >= 10:
        frappe.throw("Too many requests. Please try again later.", exc=frappe.PermissionError)
        
    frappe.cache().set_value(cache_key, count + 1, expires_in_sec=60)
