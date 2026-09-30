/**
 * The upload URL a visitor's file goes to, carrying the form's upload claim.
 *
 * The server only takes an anonymous upload on behalf of a form the visitor
 * could open (FP-SEC-08): it hands out a signed `upload_token` with the form
 * and checks it on every upload. frappe-ui's uploader forwards only a fixed
 * list of fields and drops anything else, but it does let the upload URL be
 * set -- and Frappe reads query parameters into the same request data -- so
 * the claim travels on the URL.
 *
 * Returns undefined in the builder and anywhere no public form is loaded; an
 * author's uploads are checked by Frappe's ordinary permissions instead.
 */
import { useSubmissionForm } from "@/stores/submissionForm";

export function uploadEndpointFor(fieldname?: string | null): string | undefined {
  if (!fieldname) return undefined;
  const form = useSubmissionForm().formResource?.data;
  if (!form?.name || !form?.upload_token) return undefined;

  const claim = new URLSearchParams({
    fp_form: form.name,
    fp_upload_token: form.upload_token,
    fp_field: fieldname,
  });
  return `/api/method/upload_file?${claim.toString()}`;
}
