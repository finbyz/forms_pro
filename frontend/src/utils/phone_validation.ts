import { createResource } from "frappe-ui";

/**
 * Validates a phone number against Frappe's country-code validator endpoint.
 * This runs on the specific step page so invalid numbers are flagged immediately
 * rather than failing at the final submission stage.
 */
export async function validatePhoneWithServer(
  phoneNumber: string,
  label: string = "Phone"
): Promise<{ valid: boolean; message?: string }> {
  if (!phoneNumber || !phoneNumber.trim()) {
    return { valid: true };
  }

  const val = phoneNumber.trim();

  // Basic sanity check first
  const digits = val.replace(/\D/g, "");
  if (digits.length < 6 || digits.length > 15) {
    return {
      valid: false,
      message: `${label} must be a valid phone number (6-15 digits).`,
    };
  }

  try {
    const resource = createResource({
      url: "forms_pro.api.form.validate_phone",
      params: {
        phone_number: val,
        label: label,
      },
    });
    const res: any = await resource.fetch();
    if (res && res.valid === false) {
      return { valid: false, message: res.message };
    }
    return { valid: true };
  } catch (err: any) {
    const msg =
      err?.messages?.[0] ||
      err?.message ||
      `Phone Number ${val} set in field ${label} is not valid.`;
    return { valid: false, message: msg };
  }
}
