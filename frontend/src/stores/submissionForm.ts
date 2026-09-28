import { createResource } from "frappe-ui";
import { toast } from "vue-sonner";
import { getRecaptchaToken, warmRecaptcha } from "@/utils/recaptcha";
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { FormField } from "@/types/formfield";
import { useStorage } from "@vueuse/core";
import {
  shouldFieldBeRequired,
  shouldFieldBeVisible,
} from "@/utils/conditionals";
import { useFormSteps } from "@/composables/useFormSteps";

export type UserSubmission = {
  name: string;
  creation: string;
  modified: string;
};

export enum SubmissionStatus {
  DRAFT = "Draft",
  SUBMITTED = "Submitted",
}

export const useSubmissionForm = defineStore("submissionForm", () => {
  const formResource = ref<any>(null);
  const currentFormRoute = ref<string | null>(null);
  const isLoading = computed(() => formResource.value?.loading);
  const allowIncompleteForms = computed(
    () => formResource.value?.data?.allow_incomplete
  );

  const currentFormId = computed((): string | null => {
    if (!formResource.value || !formResource.value.data) {
      return null;
    }

    return formResource.value.data.name;
  });

  const formIsPublished = computed((): boolean | null => {
    if (!formResource.value || !formResource.value.data) {
      return null;
    }

    return formResource.value.data.is_published;
  });

  const errors = ref<string[]>([]);
  const inSuccessState = ref<boolean>(false);
  /**
   * Set when the form behind this URL could not be loaded.
   *
   * The page decided it was still loading whenever `formIsPublished` was null,
   * and a failed lookup leaves it null forever -- so a mistyped or deleted
   * route sat on the spinner indefinitely instead of saying the form is not
   * there.
   */
  const loadFailed = ref(false);
  /** Id of the submission just created, for the embed's analytics event. */
  const lastSubmissionId = ref<string | null>(null);
  const inFormFillingState = ref<boolean>(true);

  const fields = ref<Record<string, any>>({});

  const allFormFields = computed<FormField[]>(
    () => formResource.value?.data?.fields || []
  );

  const {
    steps,
    currentStepIndex,
    currentStepFields,
    isMultiStep,
    isFirstStep,
    isLastStep,
    totalSteps,
    stepDirection,
    nextStep,
    prevStep,
    goToStep,
  } = useFormSteps(allFormFields, {
    /**
     * A step the author left empty is not a page a visitor should sit on --
     * they would see a heading, no fields and a Next button. The builder still
     * shows it, so it can be filled or deleted; only the live form skips it.
     *
     * The last step is always kept even when empty, because `isLastStep` is
     * what makes the Submit button appear.
     */
    dropEmptySteps: true,
  });

  function handleNextStep() {
    validateValues(currentStepFields.value);
    if (errors.value.length > 0) return;
    nextStep();
  }


  function initializeFields() {
    if (!formResource.value?.data) return;

    let _fields: Record<string, any> = {};
    formResource.value.data.fields.forEach((field: FormField) => {
      _fields[field.fieldname] = "";
      if (field.default) {
        _fields[field.fieldname] = field.default;
      }
    });

    fields.value = _fields;
  }

  async function initialize(route: string) {
    currentFormRoute.value = route;
    loadFailed.value = false;
    formResource.value = createResource({
      url: "forms_pro.api.form.get_form_by_route",
      params: {
        route: route,
      },
      onSuccess(data: any) {
        // Initialize fields with defaults first
        initializeFields();

        // Use VueUse's useStorage for reactive draft data
        const draftKey = `draft_submission_data_${data.name}`;
        const draftData = useStorage(draftKey, {}, localStorage);

        if (draftData.value && Object.keys(draftData.value).length > 0) {
          // Merge draft data with initialized fields
          fields.value = { ...fields.value, ...draftData.value };
        }

        inFormFillingState.value = true;

        // Fetch Google's script now so the first submit isn't waiting on it.
        warmRecaptcha(data.captcha_site_key);
      },
      onError() {
        // Covers both "no form with this route" and a form whose record is
        // gone; either way there is nothing to show the visitor.
        loadFailed.value = true;
      },
    });

    await formResource.value.fetch();
  }

  function saveAsDraft() {
    toast.info("Saving draft...");
    submitForm(true, true);
  }

  /**
   * Guards against a double submission.
   *
   * `isLoading` only goes true once the submit resource starts, but the
   * CAPTCHA token is awaited before that -- a round trip to Google during
   * which the Submit button is still live. A second click in that window ran
   * the whole thing again and created a second record.
   */
  const isSubmitting = ref(false);

  async function submitForm(
    is_draft: boolean = false,
    ignore_validations: boolean = false
  ) {
    if (isSubmitting.value) return;
    isSubmitting.value = true;
    try {
      return await _submitForm(is_draft, ignore_validations);
    } finally {
      isSubmitting.value = false;
    }
  }

  async function _submitForm(
    is_draft: boolean = false,
    ignore_validations: boolean = false
  ) {
    if (!ignore_validations) {
      validateValues();
      if (errors.value.length > 0) {
        return;
      }
    }

    // Drafts are the user's own in-progress work and are not CAPTCHA-checked
    // server-side, so don't burn a token on them.
    let captchaToken: string | null = null;
    if (!is_draft && formResource.value?.data?.captcha_enabled) {
      try {
        captchaToken = await getRecaptchaToken(
          formResource.value.data.captcha_site_key,
          "submit"
        );
      } catch {
        errors.value = [
          "Could not verify that you are human. Please reload the page and try again.",
        ];
        toast.error("CAPTCHA could not be loaded");
        return;
      }
    }

    const _submit_doc = createResource({
      url: "forms_pro.api.submission.submit_form_response",
      makeParams() {
        return {
          form_id: formResource.value.data.name,
          form_data: Object.entries(fields.value).map(([fieldname, value]) => ({
            fieldname: fieldname,
            value: value,
          })),
          submission_status: is_draft
            ? SubmissionStatus.DRAFT
            : SubmissionStatus.SUBMITTED,
          captcha_token: captchaToken,
        };
      },
      onSuccess(data: any) {
        clearDraft();
        // The endpoint returns the new submission's id; the embed host needs it
        // to tie a dataLayer event back to the record.
        lastSubmissionId.value = typeof data === "string" ? data : (data?.submission_id ?? null);
        if (is_draft) {
          toast.info("Draft saved successfully");
          inFormFillingState.value = true;
        } else {
          inFormFillingState.value = false;
          inSuccessState.value = true;
        }
      },
      onError(error: any) {
        toast.error("Failed to submit form");
        errors.value = error.messages?.map((message: string) => message) || [];
        if (errors.value.length === 0) {
          errors.value.push(
            "Error while submitting form. Check the values and try again."
          );
        }
      },
    });

    await _submit_doc.fetch();
  }

  // Deliberately permissive: enough to catch a typo, not so strict that it
  // rejects a legitimate address. The server re-checks anyway.
  const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  /** A phone number once punctuation is stripped: 6-15 digits, per E.164. */
  function isPlausiblePhone(value: string): boolean {
    const digits = (value ?? "").replace(/\D/g, "");
    return digits.length >= 6 && digits.length <= 15;
  }

  /** Accepts anything the browser can navigate to; the server re-checks. */
  function isPlausibleUrl(value: string): boolean {
    try {
      const url = new URL(value.includes("://") ? value : `https://${value}`);
      return !!url.hostname && url.hostname.includes(".");
    } catch {
      return false;
    }
  }

  function formatError(field: FormField, value: any): string | null {
    if (value === undefined || value === null || value === "") return null;

    if (field.fieldtype === "Email" && !EMAIL_PATTERN.test(String(value))) {
      return `${field.label} must be a valid email address`;
    }

    if (field.fieldtype === "Phone" && !isPlausiblePhone(String(value))) {
      return `${field.label} must be a valid phone number`;
    }

    if (field.fieldtype === "URL" && !isPlausibleUrl(String(value))) {
      return `${field.label} must be a valid URL (for example https://example.com)`;
    }

    if (field.fieldtype === "Number" && Number.isNaN(Number(value))) {
      return `${field.label} must be a number`;
    }

    return null;
  }

  function validateValues(fieldsToValidate?: FormField[]) {
    errors.value = [];
    const allFields = formResource.value.data.fields || [];
    const fieldsToCheck = fieldsToValidate ?? allFields;

    fieldsToCheck.forEach((field: FormField) => {
      const isVisible = shouldFieldBeVisible(field, fields.value, allFields);
      if (!isVisible) {
        return;
      }

      const isRequired = shouldFieldBeRequired(field, fields.value, allFields);
      const value = fields.value[field.fieldname];

      if (isRequired && !value) {
        errors.value.push(`${field.label} is required`);
        return;
      }

      const problem = formatError(field, value);
      if (problem) errors.value.push(problem);
    });
  }

  function clearDraft() {
    const draftKey = `draft_submission_data_${formResource.value.data.name}`;
    const draftData = useStorage(draftKey, {}, localStorage);
    draftData.value = {};
  }

  return {
    formResource,
    currentFormId,
    currentFormRoute,
    validateValues,
    fields,
    isLoading,
    allowIncompleteForms,
    errors,
    inSuccessState,
    loadFailed,
    lastSubmissionId,
    inFormFillingState,
    formIsPublished,
    initialize,
    submitForm,
    saveAsDraft,
    isSubmitting,
    steps,
    currentStepIndex,
    currentStepFields,
    isMultiStep,
    isFirstStep,
    isLastStep,
    totalSteps,
    nextStep,
    prevStep,
    goToStep,
    handleNextStep,
    stepDirection,
  };
});
