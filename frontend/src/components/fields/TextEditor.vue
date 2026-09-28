<script setup lang="ts">
import { computed } from "vue";
import { TextEditor as FrappeTextEditor } from "frappe-ui";

const props = withDefaults(
    defineProps<{
        modelValue?: string | null;
        content?: string | null;
        disabled?: boolean;
        editable?: boolean;
        inEditMode?: boolean;
        placeholder?: string;
        editorClass?: string | string[] | object;
        fixedMenu?: boolean | any[];
        bubbleMenu?: boolean | any[];
        floatingMenu?: boolean | any[];
        starterkitOptions?: any;
        field?: any;
    }>(),
    {
        modelValue: undefined,
        content: null,
        disabled: false,
        editable: undefined,
        inEditMode: false,
        placeholder: "",
        editorClass: undefined,
        fixedMenu: true,
        bubbleMenu: false,
        floatingMenu: false,
        starterkitOptions: () => ({}),
        field: undefined,
    }
);

const emit = defineEmits<{
    (e: "update:modelValue", val: string): void;
    (e: "change", val: string): void;
}>();

const editorContent = computed(() => {
    if (props.modelValue !== undefined && props.modelValue !== null) {
        return props.modelValue;
    }
    return props.content || "";
});

const isEditable = computed(() => {
    if (props.disabled) return false;
    if (props.editable !== undefined) return props.editable;
    return true;
});

const resolvedBubbleMenu = computed(() => {
    // When a fixed top toolbar is enabled, do not show floating bubble menu on text selection
    if (props.fixedMenu) {
        return false;
    }
    return props.bubbleMenu;
});

const resolvedStarterKit = computed(() => {
    return {
        heading: {
            levels: [1, 2, 3, 4, 5, 6],
        },
        ...props.starterkitOptions,
    };
});

const resolvedPlaceholder = computed(() => {
    return props.placeholder || props.field?.placeholder || "Write text here...";
});

const resolvedEditorClass = computed(() => {
    if (props.editorClass) return props.editorClass;
    return "bg-surface-white w-full rounded-b form-description border border-outline-gray-modals min-h-[6rem] p-3 focus:outline-none";
});

function onChange(val: string) {
    // frappe-ui raises `change` and `update:modelValue` together for a single
    // edit, so only one of them is listened to; both are re-emitted here for
    // parents that bind either.
    emit("update:modelValue", val);
    emit("change", val);
}
</script>

<template>
    <div class="forms-pro-text-editor w-full">
        <FrappeTextEditor
            :model-value="editorContent"
            :editable="isEditable"
            :placeholder="resolvedPlaceholder"
            :editor-class="resolvedEditorClass"
            :fixed-menu="fixedMenu"
            :bubble-menu="resolvedBubbleMenu"
            :floating-menu="floatingMenu"
            :starterkit-options="resolvedStarterKit"
            @change="onChange"
        />
    </div>
</template>

<style scoped>
.forms-pro-text-editor :deep(.ProseMirror) {
    min-height: 5rem;
}
</style>
