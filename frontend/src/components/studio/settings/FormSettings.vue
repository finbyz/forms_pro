<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { Button, FormControl, Badge } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";

const editFormStore = useEditForm();

const form = computed(() => editFormStore.formResource?.doc || {});
const original = computed(() => editFormStore.originalFormData || {});

const local = ref({
  route: "",
  access_mode: "Public" as "Public" | "Requires Login" | "Internal Only",
  record_strategy: "Create New" as "Create New" | "Update Existing" | "Collect Submission Only",
  success_mode: "Designed Page" as "Designed Page" | "Redirect to External URL",
  login_required: false,
  allow_incomplete: false,
  success_redirect_url: "",
});

const accessModeOptions = [
  { label: "Public", value: "Public" },
  { label: "Requires Login", value: "Requires Login" },
  { label: "Internal Only", value: "Internal Only" },
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

watch(() => editFormStore.formData, (data) => {
  if (data) {
    local.value = {
      route: data.route || "",
      access_mode: data.access_mode || "Public",
      record_strategy: data.record_strategy || "Create New",
      success_mode: data.success_mode || "Designed Page",
      login_required: data.login_required || false,
      allow_incomplete: data.allow_incomplete || false,
      success_redirect_url: data.success_redirect_url || "",
    };
    validateRoute();
  }
}, { immediate: true });

function validateRoute() {
  if (!local.value.route) {
    routeError.value = "";
    return;
  }
  if (!/^[a-z0-9-]+$/.test(local.value.route)) {
    routeError.value = "Route must contain only lowercase letters, numbers, and hyphens";
  } else {
    routeError.value = "";
  }
}

function saveSetting(key: string, value: any) {
  if (editFormStore.formResource?.doc) {
    editFormStore.formResource.doc[key] = value;
    editFormStore.formResource.isDirty = true;
    editFormStore.triggerAutosave();
  }
}

function updateRoute() {
  validateRoute();
  if (!routeError.value) {
    saveSetting("route", local.value.route);
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
    const scriptTag = "<" + "script async src=\"" + window.location.origin + "/api/method/forms_pro.api.v1.public.embed.get_embed_script\" data-route=\"" + local.value.route + "\" data-base=\"" + window.location.origin + "\"><" + "/script>";
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
    <div class="flex-1" style="overflow-y: auto">
      <div class="mx-auto max-w-3xl space-y-6 pb-10 px-5 py-5">
        <!-- General -->
        <section class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <span class="lucide-settings w-4 h-4 text-ink-gray-6" aria-hidden="true" />
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
                <Button variant="subtle" theme="gray" size="sm" @click="updateRoute">Save</Button>
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
            <span class="lucide-lock w-4 h-4 text-ink-gray-6" aria-hidden="true" />
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
                @change="saveSetting('access_mode', local.access_mode)"
              />
            </div>
            <div class="flex items-center justify-between pt-1">
              <div>
                <label class="text-sm text-ink-gray-8">Allow Partial Submissions</label>
                <p class="text-xs text-ink-gray-5 mt-0.5">Let users save incomplete forms</p>
              </div>
              <FormControl
                type="switch"
                size="sm"
                v-model="local.allow_incomplete"
                @change="saveSetting('allow_incomplete', local.allow_incomplete ? 1 : 0)"
              />
            </div>
          </div>
        </section>

        <!-- Submission -->
        <section class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <span class="lucide-send w-4 h-4 text-ink-gray-6" aria-hidden="true" />
            <h3 class="text-base-semibold text-ink-gray-8">Submission</h3>
          </div>
          <div class="space-y-4">
            <div class="flex items-center justify-between pt-1">
              <label class="text-sm text-ink-gray-6">Target DocType</label>
              <Badge variant="subtle" :label="form.target_doctype || 'None'" theme="blue" />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Strategy</label>
              <FormControl
                type="select"
                variant="subtle"
                size="sm"
                :options="recordStrategyOptions"
                v-model="local.record_strategy"
                @change="saveSetting('record_strategy', local.record_strategy)"
              />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-sm text-ink-gray-6">Success Mode</label>
              <FormControl
                type="select"
                variant="subtle"
                size="sm"
                :options="successModeOptions"
                v-model="local.success_mode"
                @change="saveSetting('success_mode', local.success_mode)"
              />
            </div>
          </div>
        </section>

        <!-- Success Redirect (conditional) -->
        <section v-if="local.success_mode === 'Redirect to External URL'" class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <span class="lucide-external-link w-4 h-4 text-ink-gray-6" aria-hidden="true" />
            <h3 class="text-base-semibold text-ink-gray-8">Redirect URL</h3>
          </div>
          <div class="space-y-2">
            <FormControl
              type="text"
              variant="subtle"
              size="sm"
              v-model="local.success_redirect_url"
              placeholder="https://example.com/thank-you"
              @change="saveSetting('success_redirect_url', local.success_redirect_url)"
            />
            <p class="text-xs text-ink-gray-5">Redirect users here after successful submission. Use <code class="px-1 py-0.5 bg-surface-gray-1 rounded-1 text-ink-gray-7">&#123;&#123;submission_id&#125;&#125;</code> for dynamic IDs.</p>
          </div>
        </section>

        <!-- Embed -->
        <section class="bg-surface-base rounded-6 border border-outline-gray-1 p-5">
          <div class="flex items-center gap-2 mb-5">
            <span class="lucide-globe w-4 h-4 text-ink-gray-6" aria-hidden="true" />
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
