<script setup lang="ts">
/**
 * Number input field.
 *
 * Supports configurable negative value acceptance based on `field.allow_negative`.
 * When `allow_negative` is false (default), typing minus signs or negative numbers
 * is blocked, and HTML min="0" is enforced. When enabled by admin, negative values are accepted.
 */
import { computed } from "vue";
import { FormControl } from "frappe-ui";

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
    placeholder: "",
  }
);

const allowNegative = computed(() => {
  const val = props.field?.allow_negative;
  return val === true || val === 1 || val === "1";
});

const minVal = computed(() => (allowNegative.value ? undefined : 0));

function onKeyDown(event: KeyboardEvent) {
  if (!allowNegative.value) {
    if (event.key === "-" || event.key === "Subtract") {
      event.preventDefault();
    }
  }
}

function onInput(event: Event) {
  const target = event.target as HTMLInputElement;
  if (!allowNegative.value && target && target.value) {
    const num = Number(target.value);
    if (!isNaN(num) && num < 0) {
      model.value = Math.abs(num);
    }
  }
}
</script>

<template>
  <FormControl
    type="number"
    variant="outline"
    :min="minVal"
    :disabled="disabled"
    :placeholder="placeholder || (field?.placeholder as string) || ''"
    v-model="model"
    @keydown="onKeyDown"
    @input="onInput"
  />
</template>
