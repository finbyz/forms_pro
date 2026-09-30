<script setup lang="ts">
import type { SelectOption } from "@/utils/selectOptions";
import { useFieldOptions } from "@/utils/selectOptions";
import { FormFields, formFields, FormFieldType } from "@/utils/form_fields";
import type { PropType } from "vue";
import { computed } from "vue";
import { isBooleanFieldType, toBoolean } from "@/utils/conditionals";

const props = defineProps({
    field: {
        type: Object,
        required: true,
    },
    /** Optional pre-loaded options for Select/Link fields. When not provided, options are loaded via useFieldOptions. */
    options: {
        type: Array as PropType<string[] | SelectOption[] | null>,
        required: false,
        default: undefined,
    },
    inEditMode: {
        type: Boolean,
        default: false,
    },
    disabled: {
        type: Boolean,
        default: false,
    },
});

const value = defineModel();
const fieldRef = computed(() => props.field);
const { options: loadedOptions } = useFieldOptions(fieldRef);
// `?? []` rather than `?? null`: a select handed null options throws while
// registering them, which takes the whole form down instead of showing an
// empty dropdown.
const resolvedOptions = computed(() => props.options ?? loadedOptions.value ?? []);

const getComponent = computed(() => {
    return formFields.find(
        (field: FormFields) => field.name === props.field.fieldtype
    ) as FormFieldType;
});

/**
 * A switch or checkbox is only ever handed a real `true` or `false`.
 *
 * The form holds `""` for a blank answer and `"0"` for a Check default that
 * came from a DocType. The switch underneath declares its value as a Boolean,
 * and Vue casts `""` on a Boolean prop to `true` -- so an untouched switch
 * believed it was on while being drawn off, and the first click "turned it
 * off". `"0"` is truthy in JavaScript, so a box whose value meant unticked was
 * drawn ticked. Either way what the visitor saw was not what was submitted.
 */
const isBooleanField = computed(() => isBooleanFieldType(props.field.fieldtype));

const boundValue = computed({
    get: () => (isBooleanField.value ? toBoolean(value.value) : value.value),
    set: (next) => {
        value.value = isBooleanField.value ? toBoolean(next) : next;
    },
});
</script>
<template>
    <component
        v-model="boundValue"
        :is="getComponent.component"
        :field="props.field"
        :options="resolvedOptions"
        :in-edit-mode="props.inEditMode"
        :disabled="props.disabled"
        :placeholder="props.field.placeholder || undefined"
        :maxlength="props.field.max_length ? Number(props.field.max_length) : undefined"
        v-bind="getComponent.props"
    />
</template>
