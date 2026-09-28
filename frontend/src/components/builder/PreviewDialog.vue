<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { Dialog, Button, Tooltip, ErrorMessage } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import FieldRenderer from "@/components/builder/FieldRenderer.vue";
import Heading from "@/components/fields/Heading.vue";
import PageBreak from "@/components/fields/PageBreak.vue";
import StepIndicator from "@/components/submission/StepIndicator.vue";
import { useFormSteps } from "@/composables/useFormSteps";
import { useGroupedRows } from "@/composables/useGroupedRows";
import { shouldFieldBeVisible, shouldFieldBeRequired } from "@/utils/conditionals";
import { validatePhoneWithServer } from "@/utils/phone_validation";
import type { FormField } from "@/types/formfield";

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: "close"): void }>();

const editFormStore = useEditForm();

const MODES = [
  { key: "desktop", label: "Desktop", icon: "monitor", width: "100%" },
  { key: "tablet", label: "Tablet", icon: "tablet", width: "768px" },
  { key: "mobile", label: "Mobile", icon: "smartphone", width: "375px" },
] as const;

const mode = ref<(typeof MODES)[number]>(MODES[0]);
const previewTab = ref<"form" | "success">("form");
const isLandscape = ref(false);

const previewWidth = computed(() => (isLandscape.value ? "auto" : mode.value.width));
const previewMaxWidth = computed(() => (isLandscape.value ? mode.value.width : "100%"));

const allFields = computed<FormField[]>(() => editFormStore.fields);

const {
  steps,
  currentStepIndex,
  currentStep,
  currentStepFields,
  isMultiStep,
  isFirstStep,
  isLastStep,
  totalSteps,
  stepDirection,
  nextStep,
  prevStep,
  goToStep,
} = useFormSteps(allFields);

const groupedRows = useGroupedRows(currentStepFields);

const previewValues = ref<Record<string, any>>({});
const previewErrors = ref<string[]>([]);
const formCompleted = ref(false);

const animClass = computed(() => {
  return stepDirection.value === "forward" ? "anim-forward" : "anim-back";
});

function initializePreview() {
  currentStepIndex.value = 0;
  previewErrors.value = [];
  formCompleted.value = false;
  previewTab.value = "form";

  const vals: Record<string, any> = {};
  for (const field of allFields.value) {
    vals[field.fieldname] = field.default ?? "";
  }
  previewValues.value = vals;
}

watch(
  () => props.show,
  (show) => {
    if (show) {
      initializePreview();
    }
  },
  { immediate: true }
);

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function isPlausiblePhone(value: string): boolean {
  const digits = (value ?? "").replace(/\D/g, "");
  return digits.length >= 6 && digits.length <= 15;
}

function formatError(field: FormField, value: any): string | null {
  if (value === undefined || value === null || value === "") return null;

  if (field.fieldtype === "Email" && !EMAIL_PATTERN.test(String(value))) {
    return `${field.label} must be a valid email address`;
  }

  if (field.fieldtype === "Phone" && !isPlausiblePhone(String(value))) {
    return `${field.label} must be a valid phone number`;
  }

  if (field.fieldtype === "Currency") {
    const num = Number(String(value).replace(/,/g, ""));
    if (Number.isNaN(num)) {
      return `${field.label} must be an amount`;
    }
    const allowNeg = Boolean((field as any).allow_negative);
    if (!allowNeg && num < 0) {
      return `${field.label} cannot be negative`;
    }
  }

  if (field.fieldtype === "Number") {
    const num = Number(value);
    if (Number.isNaN(num)) {
      return `${field.label} must be a number`;
    }
    const allowNeg = Boolean((field as any).allow_negative);
    if (!allowNeg && num < 0) {
      return `${field.label} cannot be negative`;
    }
  }

  return null;
}

function isFieldVisible(field: FormField) {
  return shouldFieldBeVisible(field, previewValues.value, allFields.value);
}

function isFieldRequired(field: FormField) {
  return shouldFieldBeRequired(field, previewValues.value, allFields.value);
}

function validateStepFields(fieldsToValidate?: FormField[]): boolean {
  previewErrors.value = [];
  const fieldsToCheck = fieldsToValidate ?? currentStepFields.value;

  fieldsToCheck.forEach((field: FormField) => {
    const isVisible = isFieldVisible(field);
    if (!isVisible) return;

    const isRequired = isFieldRequired(field);
    const value = previewValues.value[field.fieldname];

    if (
      isRequired &&
      (value === undefined ||
        value === null ||
        value === "" ||
        (Array.isArray(value) && value.length === 0))
    ) {
      previewErrors.value.push(`${field.label} is required`);
      return;
    }

    const problem = formatError(field, value);
    if (problem) previewErrors.value.push(problem);
  });

  return previewErrors.value.length === 0;
}

async function handleNextStep() {
  if (!validateStepFields(currentStepFields.value)) {
    return;
  }
  previewErrors.value = [];

  const phoneFields = (currentStepFields.value || []).filter(
    (field: FormField) => field.fieldtype === "Phone" && previewValues.value[field.fieldname]
  );

  for (const pf of phoneFields) {
    const val = String(previewValues.value[pf.fieldname] || "").trim();
    if (!val) continue;
    const res = await validatePhoneWithServer(val, pf.label || pf.fieldname);
    if (!res.valid) {
      previewErrors.value.push(
        res.message || `Phone Number ${val} set in field ${pf.label || pf.fieldname} is not valid.`
      );
      return;
    }
  }

  nextStep();
}

function handlePrevStep() {
  previewErrors.value = [];
  prevStep();
}

function handleGoToStep(index: number) {
  previewErrors.value = [];
  goToStep(index);
}

function handleSubmit() {
  if (!validateStepFields(currentStepFields.value)) {
    return;
  }
  previewErrors.value = [];
  formCompleted.value = true;
  previewTab.value = "success";
}

function isHeading(field: any): boolean {
  return ["Heading 1", "Heading 2", "Heading 3"].includes(field.fieldtype);
}

function isPageBreak(field: any): boolean {
  return field.fieldtype === "Page Break";
}

// Dialog v-model bridge
const isOpen = computed({
  get: () => props.show,
  set: (val: boolean) => {
    if (!val) emit("close");
  },
});

const dialogOptions = { title: "Preview", size: "7xl" as const };
const formData = computed(() => editFormStore.formData);

// Parse success blocks from form data for read-only rendering
interface SuccessBlock {
  id: string;
  type: string;
  content: string;
  style: Record<string, string>;
}

const successBlocks = computed<SuccessBlock[]>(() => {
  if (!formData.value?.success_schema_json) return [];
  try {
    return JSON.parse(formData.value.success_schema_json);
  } catch {
    return [];
  }
});
</script>

<template>
  <Dialog v-model="isOpen" :options="dialogOptions">
    <template #body>
      <div class="bg-surface-modal rounded-xl">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-outline-gray-1">
          <span class="text-lg font-semibold text-ink-gray-9">Preview</span>
          <div class="flex items-center gap-2">
            <Tooltip text="Rotate" placement="bottom">
              <Button variant="ghost" size="sm" icon="rotate-cw" @click="isLandscape = !isLandscape" />
            </Tooltip>
            <Button variant="ghost" size="sm" icon="x" @click="emit('close')" />
          </div>
        </div>

        <div class="flex flex-col gap-4 p-6 min-h-[640px]">
          <!-- Mode selector -->
          <div class="flex items-center justify-center gap-2">
            <Button
              v-for="m in MODES"
              :key="m.key"
              :variant="mode.key === m.key ? 'subtle' : 'ghost'"
              theme="gray"
              size="sm"
              @click="mode = m"
              :disabled="isLandscape"
              :icon-left="m.icon"
              :label="m.label"
            />
          </div>

          <!-- Tab selector -->
          <div class="flex justify-center gap-1 bg-surface-gray-2 p-1 rounded-lg w-fit mx-auto">
            <button
              class="px-4 py-1.5 text-sm font-medium rounded-md transition-all"
              :class="
                previewTab === 'form'
                  ? 'bg-surface-white text-ink-gray-9 shadow-sm'
                  : 'text-ink-gray-6 hover:text-ink-gray-8'
              "
              @click="previewTab = 'form'"
            >
              Form
            </button>
            <button
              class="px-4 py-1.5 text-sm font-medium rounded-md transition-all"
              :class="
                previewTab === 'success'
                  ? 'bg-surface-white text-ink-gray-9 shadow-sm'
                  : 'text-ink-gray-6 hover:text-ink-gray-8'
              "
              @click="previewTab = 'success'"
            >
              Success Page
            </button>
          </div>

          <!-- Preview canvas -->
          <div class="flex justify-center flex-1 min-h-0">
            <div
              class="border border-outline-gray-2 rounded-xl bg-surface-white overflow-auto shadow-sm preview-canvas flex flex-col"
              :style="{ width: previewWidth, maxWidth: previewMaxWidth }"
            >
              <!-- Browser chrome bar (Desktop/Tablet) -->
              <div
                v-if="!isLandscape && mode.key !== 'mobile'"
                class="flex items-center justify-between px-4 h-9 bg-surface-gray-1 rounded-t-xl border-b border-outline-gray-1 shrink-0"
              >
                <div class="flex gap-1.5">
                  <div class="size-2.5 rounded-full bg-red-400" aria-hidden="true" />
                  <div class="size-2.5 rounded-full bg-amber-400" aria-hidden="true" />
                  <div class="size-2.5 rounded-full bg-green-400" aria-hidden="true" />
                </div>
                <div class="text-[11px] text-ink-gray-4 font-mono">{{ mode.label }} Preview</div>
                <div class="flex gap-1.5">
                  <div class="size-2.5 rounded-full bg-surface-gray-3" aria-hidden="true" />
                  <div class="size-2.5 rounded-full bg-surface-gray-3" aria-hidden="true" />
                  <div class="size-2.5 rounded-full bg-surface-gray-3" aria-hidden="true" />
                </div>
              </div>

              <!-- Content area -->
              <div
                :class="mode.key === 'mobile' || isLandscape ? 'p-4 sm:p-6' : 'p-6 sm:p-8'"
                class="min-h-[420px] flex-1 flex flex-col justify-between"
              >
                <!-- Form view -->
                <div v-if="previewTab === 'form'" class="flex flex-col flex-1 justify-between gap-6">
                  <div>
                    <!-- Step Indicator -->
                    <div v-if="isMultiStep" class="mb-6 pb-2 border-b border-outline-gray-1">
                      <StepIndicator
                        :steps="steps"
                        :currentIndex="currentStepIndex"
                        @go-to="handleGoToStep"
                      />
                    </div>

                    <!-- Step 2+ compact header for multi-step -->
                    <div
                      v-if="isMultiStep && !isFirstStep"
                      class="flex items-center gap-3 pb-4 mb-4 border-b border-outline-gray-1"
                    >
                      <div class="flex-1 min-w-0">
                        <div class="text-[11px] text-ink-gray-4 font-medium tracking-wider uppercase mb-0.5">
                          Step {{ currentStepIndex + 1 }} of {{ totalSteps }}
                        </div>
                        <h3 class="text-lg font-bold text-ink-gray-9 tracking-tight truncate">
                          {{ currentStep?.label || `Step ${currentStepIndex + 1}` }}
                        </h3>
                      </div>
                      <div
                        class="flex items-center gap-1 px-2.5 py-1 rounded-full bg-surface-gray-2 text-[11px] font-semibold text-ink-gray-5 tabular-nums shrink-0"
                      >
                        {{ currentStepFields.length }} field{{ currentStepFields.length !== 1 ? "s" : "" }}
                      </div>
                    </div>

                    <!-- Step animated container with fields -->
                    <div :key="currentStepIndex" :class="animClass" class="space-y-4">
                      <template v-for="(row, rowIdx) in groupedRows" :key="rowIdx">
                        <div
                          v-if="row.some((col) => col.some(isFieldVisible))"
                          :class="mode.key === 'mobile' ? 'flex flex-col gap-4' : 'flex gap-5'"
                        >
                          <div
                            v-for="(col, cIdx) in row"
                            :key="cIdx"
                            v-show="col.some(isFieldVisible)"
                            class="flex-1 space-y-3 min-w-0"
                          >
                            <template v-for="field in col" :key="field.name || field.fieldname">
                              <div v-if="isFieldVisible(field)">
                                <Heading v-if="isHeading(field)" :field="field" />
                                <PageBreak v-else-if="isPageBreak(field)" :field="field" :inEditMode="false" />
                                <FieldRenderer
                                  v-else
                                  v-model="previewValues[field.fieldname]"
                                  :field="{
                                    ...field,
                                    reqd: isFieldRequired(field),
                                  }"
                                  :inEditMode="false"
                                />
                              </div>
                            </template>
                          </div>
                        </div>
                      </template>
                    </div>

                    <!-- Validation Errors -->
                    <div v-if="previewErrors.length > 0" class="mt-4">
                      <hr class="mb-3 border-outline-gray-1" />
                      <ErrorMessage :message="previewErrors.join('\n')" />
                    </div>
                  </div>

                  <!-- Footer Navigation -->
                  <div class="flex items-center justify-between pt-6 border-t border-outline-gray-1 mt-6">
                    <!-- Multi-step progress pills -->
                    <div v-if="isMultiStep" class="flex items-center gap-1.5">
                      <div
                        v-for="idx in totalSteps"
                        :key="idx"
                        class="h-[5px] rounded-full transition-all duration-[280ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
                        :class="{
                          'w-1.5 bg-gray-400': idx - 1 < currentStepIndex,
                          'w-5 bg-gray-800': idx - 1 === currentStepIndex,
                          'w-1.5 bg-gray-200': idx - 1 > currentStepIndex,
                        }"
                      />
                    </div>
                    <div v-else />

                    <!-- Buttons -->
                    <div class="flex items-center gap-2">
                      <Button
                        v-if="isMultiStep && !isFirstStep"
                        variant="subtle"
                        @click="handlePrevStep"
                      >
                        Back
                      </Button>
                      <Button
                        v-if="!isLastStep"
                        variant="solid"
                        @click="handleNextStep"
                      >
                        <span class="flex items-center gap-1.5">
                          Next
                          <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                        </span>
                      </Button>
                      <Button
                        v-else
                        variant="solid"
                        @click="handleSubmit"
                      >
                        Submit
                      </Button>
                    </div>
                  </div>
                </div>

                <!-- Success Page view -->
                <div v-else-if="previewTab === 'success'" class="flex flex-col items-center gap-3 py-8">
                  <template v-if="successBlocks.length === 0">
                    <div class="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-2xl font-bold">✓</div>
                    <h2 class="text-xl font-semibold text-gray-900">Thank you!</h2>
                    <p class="text-sm text-gray-500">Your response has been recorded.</p>
                  </template>
                  <template v-else v-for="block in successBlocks" :key="block.id">
                    <div v-if="block.type === 'icon'" class="flex justify-center">
                      <div class="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-2xl font-bold">{{ block.content }}</div>
                    </div>
                    <h2 v-else-if="block.type === 'heading'" class="text-xl font-semibold text-center">{{ block.content || "Heading" }}</h2>
                    <p v-else-if="block.type === 'paragraph'" class="text-sm text-gray-600 text-center max-w-md">{{ block.content || "Text" }}</p>
                    <hr v-else-if="block.type === 'divider'" class="border-gray-200 w-full" />
                    <div v-else-if="block.type === 'spacer'" class="h-6" />
                    <div v-else-if="block.type === 'button'" class="flex justify-center">
                      <span class="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg">{{ block.content || "Button" }}</span>
                    </div>
                    <code v-else-if="block.type === 'reference'" class="text-xs bg-gray-100 px-3 py-1.5 rounded text-center block text-gray-600">{{ block.content }}</code>
                    <div v-else-if="block.type === 'summary'" class="text-xs bg-gray-50 px-4 py-3 rounded text-center text-gray-600 w-full">{{ block.content }}</div>
                    <div v-else-if="block.type === 'steps'" class="text-sm text-gray-600 space-y-2 w-full max-w-sm">
                      <div v-for="(line, i) in block.content.split('\n')" :key="i" class="flex items-center gap-2">
                        <span class="w-5 h-5 flex items-center justify-center bg-blue-100 text-blue-600 rounded-full text-xs font-medium shrink-0">{{ i + 1 }}</span>
                        <span>{{ line }}</span>
                      </div>
                    </div>
                  </template>

                  <Button
                    v-if="formCompleted"
                    variant="subtle"
                    size="sm"
                    class="mt-6"
                    @click="initializePreview"
                  >
                    Restart Preview
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.preview-canvas {
  transition: width 200ms ease-out, max-width 200ms ease-out;
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(22px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-22px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.anim-forward {
  animation: slideInRight 0.22s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.anim-back {
  animation: slideInLeft 0.22s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

@media (prefers-reduced-motion: reduce) {
  .preview-canvas,
  .anim-forward,
  .anim-back {
    animation: none !important;
    transition: none !important;
  }
}
</style>
