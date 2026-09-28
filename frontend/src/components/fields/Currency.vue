<script setup lang="ts">
/**
 * Currency input field.
 *
 * Renders a numeric input with a currency symbol prefix (e.g. $, €, kr, CHF, ₹),
 * right-aligned formatting with thousand separators on blur, and clean numeric
 * values for submission. Matches Frappe Desk's Currency field conventions.
 */
import { computed, ref, watch } from "vue";
import { FormControl } from "frappe-ui";
import {
  getCurrencySymbol,
  formatCurrencyAmount,
  cleanCurrencyInput,
} from "@/utils/currencies";

const model = defineModel<string | number | null>();

const props = withDefaults(
  defineProps<{
    field?: Record<string, any>;
    disabled?: boolean;
    inEditMode?: boolean;
    placeholder?: string;
  }>(),
  {
    field: () => ({}),
    disabled: false,
    inEditMode: false,
    placeholder: "0.00",
  }
);

const isFocused = ref(false);
const rawValue = ref<string>("");

// Resolve currency symbol from field.options or site default
const symbol = computed(() => {
  return getCurrencySymbol(props.field?.options);
});

// Format value for display when blurred
const formattedValue = computed(() => {
  if (model.value === null || model.value === undefined || model.value === "") {
    return "";
  }
  return formatCurrencyAmount(model.value);
});

// Synchronize rawValue when external model changes
watch(
  () => model.value,
  (newVal) => {
    if (!isFocused.value) {
      rawValue.value = newVal !== null && newVal !== undefined ? cleanCurrencyInput(String(newVal)) : "";
    }
  },
  { immediate: true }
);

const allowNegative = computed(() => {
  const val = props.field?.allow_negative;
  return val === true || val === 1 || val === "1";
});

function onKeyDown(event: KeyboardEvent) {
  if (!allowNegative.value && (event.key === "-" || event.key === "Subtract")) {
    event.preventDefault();
  }
}

function onFocus() {
  if (props.disabled || props.field?.read_only) return;
  isFocused.value = true;
  rawValue.value = model.value !== null && model.value !== undefined ? cleanCurrencyInput(String(model.value)) : "";
}

function onBlur() {
  isFocused.value = false;
  if (!rawValue.value) {
    model.value = "";
    return;
  }
  let clean = cleanCurrencyInput(rawValue.value);
  if (!allowNegative.value) {
    clean = clean.replace(/-/g, "");
  }
  const num = Number(clean);
  if (!Number.isNaN(num)) {
    model.value = clean;
  } else {
    model.value = rawValue.value;
  }
}

function onInput(val: any) {
  let text = typeof val === "string" ? val : val?.target?.value ?? "";
  if (!allowNegative.value) {
    text = text.replace(/-/g, "");
  }
  rawValue.value = text;
  model.value = cleanCurrencyInput(text);
}
</script>

<template>
  <div class="relative w-full">
    <FormControl
      type="text"
      :model-value="isFocused ? rawValue : formattedValue"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeyDown"
      @update:model-value="onInput"
      :disabled="disabled || field?.read_only"
      :placeholder="placeholder || '0.00'"
      variant="outline"
      class="w-full"
    >
      <template #prefix>
        <span class="text-sm font-medium text-ink-gray-6 select-none pl-1 pr-0.5">
          {{ symbol }}
        </span>
      </template>
    </FormControl>
  </div>
</template>
