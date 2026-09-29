<script setup lang="ts">
import { ref, watch, computed, defineAsyncComponent } from "vue";
import { Button, FormControl, Badge, createResource } from "frappe-ui";

// Same reason as everywhere else: keep ProseMirror out of the eager graph.
const TextEditor = defineAsyncComponent(() => import("@/components/fields/TextEditor.vue"));
import { useEditForm } from "@/stores/editForm";
import { validateFormRoute } from "@/utils/form_generator";
import { toast } from "vue-sonner";

const editFormStore = useEditForm();

const form = computed(() => editFormStore.formResource?.doc || {});
const original = computed(() => editFormStore.originalFormData || {});

const local = ref({
  route: "",
  access_mode: "Public" as "Public" | "Requires Login" | "Internal Only",
  record_strategy: "Create New" as "Create New" | "Update Existing" | "Collect Submission Only",
  create_target_fields: false,
  naming_pattern: "",
  success_title: "",
  success_description: "",
  success_mode: "Designed Page" as "Designed Page" | "Redirect to External URL",
  login_required: false,
  allow_incomplete: false,
  success_redirect_url: "",
});

/** Placeholders for this form's own answers, to show beside the pattern box. */
const NOT_NAMEABLE = new Set([
    "Heading 1", "Heading 2", "Heading 3", "Page Break",
    "Table", "Multiselect", "Attach",
]);

const namingFieldTokens = computed(() =>
    (editFormStore.formData?.fields ?? [])
        .filter((f: any) => f.fieldname && !NOT_NAMEABLE.has(f.fieldtype))
        .map((f: any) => `{${f.fieldname}}`)
);

const accessModeOptions = [
  { label: "Public", value: "Public" },
  { label: "Requires Login", value: "Requires Login" },
] as const;

const recordStrategyOptions = [
  { label: "Create New", value: "Create New" },
  { label: "Update Existing", value: "Update Existing" },
  { label: "Collect Submission Only", value: "Collect Submission Only" },
] as const;

const successModeOptions = [
  { label: "Designed Page", value: "Designed Page" },
  { label: "Redirect to External URL", value: "Redirect to External URL" },
] as const;

const routeError = ref("");

// A form with no target_doctype has nothing to offer in the builder's DocType
// sidebar, and there was previously no way to set one after creation.
const doctypeList = createResource({
  url: "forms_pro.api.form.get_doctype_list",
  method: "GET",
  auto: true,
});

const doctypeOptions = computed(() =>
  (doctypeList.data ?? []).map((name: string) => ({ label: name, value: name }))
);

async function setTargetDoctype(value: string) {
  const { changed, seeded, hadMappings } = await editFormStore.setTargetDoctype(value);
  if (!changed) return;
  if (hadMappings) {
    toast.warning(
      "Target DocType changed — existing field mappings point at the old DocType and need review."
    );
  } else if (seeded) {
    toast.success(`Added ${seeded} required field${seeded === 1 ? "" : "s"} from ${value}`);
  }
}

// The panel is a local copy of the document, so it has to be refilled whenever
// the form loads or is replaced by a save response. Without this the controls
// keep their initial defaults and every visit looks like the change was lost.
watch(
    () => editFormStore.formData,
    (data) => {
        if (!data) return;
        local.value = {
            route: data.route ?? "",
            // Keep the two in step: a legacy form may carry login_required
            // without a matching access_mode.
            access_mode:
                data.access_mode === "Requires Login" || data.login_required
                    ? "Requires Login"
                    : "Public",
            record_strategy: data.record_strategy ?? "Create New",
            create_target_fields: Boolean(data.create_target_fields),
            naming_pattern: data.naming_pattern ?? "",
            success_title: data.success_title ?? "",
            success_description: data.success_description ?? "",
            success_mode: data.success_mode ?? "Designed Page",
            login_required: !!data.login_required,
            allow_incomplete: !!data.allow_incomplete,
            success_redirect_url: data.success_redirect_url ?? "",
        };
        routeError.value = "";
    },
    { immediate: true, deep: true }
);

const ROUTE_PATTERN = /^[a-z0-9]+(?:[-_][a-z0-9]+)*$/;

/**
 * Validate the public route: format first (cheap), then uniqueness against
 * other forms. Returns true when the route is usable.
 */
async function validateRoute(): Promise<boolean> {
  const route = (local.value.route || "").trim();

  if (!route) {
    routeError.value = "Route cannot be empty.";
    return false;
  }
  if (!ROUTE_PATTERN.test(route)) {
    routeError.value =
      "Use lowercase letters, numbers, hyphens or underscores (e.g. solar-enquiry).";
    return false;
  }

  try {
    const taken = await validateFormRoute(editFormStore.currentFormId ?? "", route);
    if (taken) {
      routeError.value = "That route is already used by another form.";
      return false;
    }
  } catch {
    routeError.value = "Could not check the route. Please try again.";
    return false;
  }

  routeError.value = "";
  return true;
}

/** "Requires Login" is the single source of truth for login_required. */
function updateAccessMode(val: any) {
  const mode = typeof val === "string" ? val : val?.value || "Public";
  local.value.access_mode = mode;
  saveSetting("access_mode", mode);
  const requiresLogin = mode === "Requires Login";
  local.value.login_required = requiresLogin;
  saveSetting("login_required", requiresLogin ? 1 : 0);
}

function updateAllowIncomplete(val: any) {
  const checked = Boolean(val);
  local.value.allow_incomplete = checked;
  saveSetting("allow_incomplete", checked ? 1 : 0);
}

function updateRecordStrategy(val: any) {
  const strategy = typeof val === "string" ? val : val?.value || "Create New";
  local.value.record_strategy = strategy;
  saveSetting("record_strategy", strategy);
}

function updateSuccessMode(val: any) {
  const mode = typeof val === "string" ? val : val?.value || "Designed Page";
  local.value.success_mode = mode;
  saveSetting("success_mode", mode);
}

function updateSuccessRedirectUrl(val: any) {
  const url = typeof val === "string" ? val : val?.target?.value || "";
  local.value.success_redirect_url = url;
  saveSetting("success_redirect_url", url);
}

function saveSetting(key: string, value: any) {
  if (editFormStore.formResource?.doc) {
    editFormStore.formResource.doc[key] = value;
    editFormStore.formResource.isDirty = true;
    editFormStore.triggerAutosave();
  }
}

const savingRoute = ref(false);

async function updateRoute() {
  savingRoute.value = true;
  try {
    if (!(await validateRoute())) return;
    saveSetting("route", local.value.route.trim());
    toast.success("Route updated");
  } finally {
    savingRoute.value = false;
  }
}

function copyLink() {
  const link = `${window.location.origin}/forms/p/${local.value.route}`;
  navigator.clipboard.writeText(link);
  (window as any).frappe?.show_alert?.({ message: "Link copied!", indicator: "green" });
}

function copyEmbed() {
    const link = `${window.location.origin}/forms/p/${local.value.route}`;
    // Avoid Vue compiler parsing script tags in template literal
    // Not `async`: the loader identifies itself from the running tag, and an
    // async tag can execute out of order. Same snippet as the Share panel.
    const scriptTag = "<" + "script src=\"" + window.location.origin + "/api/method/forms_pro.api.v1.public.get_embed_script\" data-route=\"" + local.value.route + "\" data-base=\"" + window.location.origin + "\"><" + "/script>";
    const code = `<div data-forms-pro="${local.value.route}"></div>
${scriptTag}`;
    navigator.clipboard.writeText(code);
    (window as any).frappe?.show_alert?.({ message: "Embed code copied!", indicator: "green" });
}
</script>

<template>
  <div class="flex flex-col h-full bg-surface-base">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-outline-gray-1 bg-surface-base">
      <div>
        <h2 class="text-lg-semibold text-ink-gray-9">Form Settings</h2>
        <p class="text-sm text-ink-gray-5 mt-0.5">Configure form behavior and access</p>
      </div>
    </div>

    <!-- Content with scroll -->
    <div class="flex-1 overflow-y-auto">
      <div class="mx-auto max-w-3xl space-y-6 pb-10 px-5 py-5">
        <!-- General -->
        <section class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <lucide-settings class="w-4 h-4 text-ink-gray-6" aria-hidden="true" />
            <h3 class="text-base-semibold text-ink-gray-8">General</h3>
          </div>
          <div class="space-y-4">
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Route</label>
              <div class="flex items-start gap-2">
                <span class="text-sm text-ink-gray-5 leading-8 shrink-0">/forms/p/</span>
                <div class="flex-1 space-y-1">
                  <FormControl
                    type="text"
                    variant="subtle"
                    size="sm"
                    v-model="local.route"
                    @blur="validateRoute"
                    placeholder="my-form"
                  />
                  <p v-if="routeError" class="text-xs text-ink-red-7">{{ routeError }}</p>
                </div>
                <Button
                  variant="subtle"
                  theme="gray"
                  size="sm"
                  :loading="savingRoute"
                  @click="updateRoute"
                >Save</Button>
              </div>
            </div>
            <div class="flex items-center justify-between pt-1">
              <label class="text-sm text-ink-gray-6">Status</label>
              <Badge variant="subtle" :label="form.status || 'Draft'" theme="gray" />
            </div>
          </div>
        </section>

        <!-- Access -->
        <section class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <lucide-lock class="w-4 h-4 text-ink-gray-6" aria-hidden="true" />
            <h3 class="text-base-semibold text-ink-gray-8">Access</h3>
          </div>
          <div class="space-y-4">
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Access Mode</label>
              <FormControl
                type="select"
                variant="subtle"
                size="sm"
                :options="accessModeOptions"
                v-model="local.access_mode"
                @update:modelValue="updateAccessMode"
              />
            </div>
            <div class="flex items-center justify-between pt-1">
              <div>
                <label class="text-sm text-ink-gray-8">Allow Partial Submissions</label>
                <p class="text-xs text-ink-gray-5 mt-0.5">Let users save incomplete forms</p>
              </div>
              <FormControl
                type="checkbox"
                size="sm"
                v-model="local.allow_incomplete"
                @update:modelValue="updateAllowIncomplete"
              />
            </div>
          </div>
        </section>

        <!-- Submission -->
        <section class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <lucide-send class="w-4 h-4 text-ink-gray-6" aria-hidden="true" />
            <h3 class="text-base-semibold text-ink-gray-8">Submission</h3>
          </div>
          <div class="space-y-4">
            <div class="flex flex-col gap-2 pt-1">
              <div class="flex items-center justify-between gap-2">
                <label class="text-sm text-ink-gray-6">Target DocType</label>
                <div class="flex items-center gap-1.5">
                  <!--
                    Whether the form generated this DocType or was pointed at
                    one the site already had. It decides what the form is
                    allowed to change, so it belongs next to the name.
                  -->
                  <Badge
                    v-if="form.target_doctype"
                    variant="subtle"
                    :theme="form.owns_target_doctype ? 'blue' : 'orange'"
                    :label="form.owns_target_doctype ? 'Created by this form' : 'Existing DocType'"
                  />
                  <Badge
                    variant="subtle"
                    :label="form.target_doctype || 'Not set'"
                    :theme="form.target_doctype ? 'blue' : 'orange'"
                  />
                </div>
              </div>
              <FormControl
                type="autocomplete"
                variant="subtle"
                size="sm"
                placeholder="Search DocType…"
                :options="doctypeOptions"
                :modelValue="form.target_doctype"
                @update:modelValue="(v: { value: string } | string) => setTargetDoctype(typeof v === 'string' ? v : v?.value)"
              />
              <p v-if="!form.target_doctype" class="text-xs text-ink-gray-5">
                Set this to list that DocType's fields in the builder sidebar.
              </p>
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Strategy</label>
              <FormControl
                type="select"
                variant="subtle"
                size="sm"
                :options="recordStrategyOptions"
                v-model="local.record_strategy"
                @update:modelValue="updateRecordStrategy"
              />
            </div>
            <div class="flex items-start justify-between gap-4 pt-1">
              <div>
                <label class="text-sm text-ink-gray-8">Create Missing Fields on {{ form.target_doctype || "Target DocType" }}</label>
                <p class="text-xs text-ink-gray-5 mt-0.5 max-w-md">
                  Answers whose field does not exist on the target are kept only in the
                  submission. Turn this on to add them as custom fields, grouped in their
                  own tab.
                </p>
              </div>
              <FormControl
                type="checkbox"
                size="sm"
                v-model="local.create_target_fields"
                @change="saveSetting('create_target_fields', local.create_target_fields ? 1 : 0)"
              />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Record Name Pattern</label>
              <FormControl
                type="text"
                variant="subtle"
                size="sm"
                placeholder="ENQ-{YYYY}-{#####}"
                v-model="local.naming_pattern"
                @change="saveSetting('naming_pattern', local.naming_pattern)"
              />
              <p class="text-xs text-ink-gray-5">
                Leave blank for generated ID. Tokens: <code class="rounded bg-surface-gray-2 px-1">{#####}</code>, <code class="rounded bg-surface-gray-2 px-1">{YYYY}</code>, <code class="rounded bg-surface-gray-2 px-1">{MM}</code>, <code class="rounded bg-surface-gray-2 px-1">{fieldname}</code>
              </p>
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Success Mode</label>
              <FormControl
                type="select"
                variant="subtle"
                size="sm"
                :options="successModeOptions"
                v-model="local.success_mode"
                @update:modelValue="updateSuccessMode"
              />
            </div>
          </div>
        </section>

        <!-- Thank-you message (conditional) -->
        <section
          v-if="local.success_mode === 'Designed Page'"
          class="bg-surface-base rounded-6 border border-outline-gray-1 p-5"
        >
          <div class="flex items-center gap-2 mb-5">
            <lucide-message-square class="w-4 h-4 text-ink-gray-6" aria-hidden="true" />
            <h3 class="text-base-semibold text-ink-gray-8">Thank-you Message</h3>
          </div>
          <div class="space-y-4">
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Title</label>
              <FormControl
                type="text"
                variant="subtle"
                size="sm"
                placeholder="Thanks for getting in touch"
                v-model="local.success_title"
                @change="saveSetting('success_title', local.success_title)"
              />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Description</label>
              <TextEditor
                variant="outline"
                :content="local.success_description"
                editor-class="bg-surface-white w-full rounded-b form-description border rounded-b min-h-24"
                placeholder="Tell them what happens next"
                :bubble-menu="true"
                @change="
                  (value: string) => {
                    local.success_description = value;
                    saveSetting('success_description', value);
                  }
                "
              />
            </div>
            <p class="text-xs text-ink-gray-5">
              Shown on the success page after a visitor submits.
            </p>
          </div>
        </section>

        <!-- Success Redirect (conditional) -->
        <section v-if="local.success_mode === 'Redirect to External URL'" class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <lucide-external-link class="w-4 h-4 text-ink-gray-6" aria-hidden="true" />
            <h3 class="text-base-semibold text-ink-gray-8">Redirect URL</h3>
          </div>
          <div class="space-y-2">
            <FormControl
              type="text"
              variant="subtle"
              size="sm"
              v-model="local.success_redirect_url"
              placeholder="https://example.com/thank-you"
              @update:modelValue="updateSuccessRedirectUrl"
            />
            <p class="text-xs text-ink-gray-5">Redirect users here after successful submission. Use <code class="px-1 py-0.5 bg-surface-gray-1 rounded-1 text-ink-gray-7">&#123;&#123;submission_id&#125;&#125;</code> for dynamic IDs.</p>
          </div>
        </section>

        <!-- Embed -->
        <section class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <lucide-globe class="w-4 h-4 text-ink-gray-6" aria-hidden="true" />
            <h3 class="text-base-semibold text-ink-gray-8">Embed</h3>
          </div>
          <div class="space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <Button 
                icon-left="copy" 
                variant="subtle" 
                theme="gray" 
                size="sm" 
                @click="copyLink"
              >
                Copy Link
              </Button>
              <Button 
                icon-left="code" 
                variant="subtle" 
                theme="gray" 
                size="sm" 
                @click="copyEmbed"
              >
                Copy Embed Code
              </Button>
            </div>
            <p class="text-xs text-ink-gray-5">Share this form on any website via embed code or direct link</p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
