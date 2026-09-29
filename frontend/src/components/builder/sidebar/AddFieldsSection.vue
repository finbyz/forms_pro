<script setup lang="ts">
import { ref, computed } from "vue";
import draggableComponent from "vuedraggable";
import { FormControl } from "frappe-ui";
import { ChevronRight } from "@lucide/vue";
import { formFields, type FormFields } from "@/utils/form_fields";
import { Fieldtype } from "@/types/FormsPro/form_field.types";
import { useEditForm } from "@/stores/editForm";

const editFormStore = useEditForm();
const search = ref("");

const HIDDEN_FROM_SIDEBAR = new Set<string>([
    // Page Break is added via the step controls, not as a draggable field.
    Fieldtype.PAGE_BREAK,

    // Link is withheld until a client asks for it. Choosing a DocType here
    // means the visitors filling the form can list that DocType's records --
    // that is the field doing its job, but it is a decision about who may see
    // what, and not one to make by dropping a field on a canvas. Delete this
    // line to put it back; nothing else is needed, and Link fields that a form
    // already has, or that came from the target DocType, keep working.
    Fieldtype.LINK,
]);

const CATEGORIES: { label: string; fieldNames: Fieldtype[] }[] = [
    {
        label: "Basic",
        fieldNames: [
            Fieldtype.DATA,
            Fieldtype.NUMBER,
            Fieldtype.CURRENCY,
            Fieldtype.EMAIL,
            Fieldtype.PHONE,
            Fieldtype.URL,
            Fieldtype.TEXTAREA,
            Fieldtype.TEXT_EDITOR,
        ],
    },
    {
        label: "Choice",
        fieldNames: [
            Fieldtype.SELECT,
            Fieldtype.MULTISELECT,
            Fieldtype.CHECKBOX,
            Fieldtype.SWITCH,
            Fieldtype.RATING,
            Fieldtype.LANGUAGE,
        ],
    },
    {
        label: "Date & Time",
        fieldNames: [
            Fieldtype.DATE,
            Fieldtype.DATE_TIME,
            Fieldtype.DATE_RANGE,
            Fieldtype.TIME_PICKER,
        ],
    },
    { label: "Upload", fieldNames: [Fieldtype.ATTACH] },
    {
        label: "Layout",
        fieldNames: [Fieldtype.HEADING_1, Fieldtype.HEADING_2, Fieldtype.HEADING_3],
    },
    {
        label: "Advanced",
        fieldNames: [Fieldtype.LINK, Fieldtype.PASSWORD, Fieldtype.TABLE],
    },
];

const visibleFields = computed(() =>
    formFields.filter((f: FormFields) => !HIDDEN_FROM_SIDEBAR.has(f.name))
);

const hasSearch = computed(() => search.value.trim().length > 0);

const searchResults = computed(() => {
    const q = search.value.trim().toLowerCase();
    return visibleFields.value.filter((f: FormFields) => f.name.toLowerCase().includes(q));
});

// A field type that no category claims used to vanish from the palette with
// no error anywhere -- it simply could not be added to a form. Anything
// uncategorised is collected here instead of being silently dropped.
const categorised = new Set<string>(CATEGORIES.flatMap((c) => c.fieldNames));

const groups = computed(() =>
    [
        ...CATEGORIES.map((cat) => ({
            label: cat.label,
            fields: visibleFields.value.filter((f: FormFields) =>
                cat.fieldNames.includes(f.name as Fieldtype)
            ),
        })),
        {
            label: "Other",
            fields: visibleFields.value.filter((f: FormFields) => !categorised.has(f.name)),
        },
    ].filter((g) => g.fields.length > 0)
);

// Collapsed categories, remembered per browser.
const collapsed = ref<Record<string, boolean>>(readCollapsed());

function readCollapsed(): Record<string, boolean> {
    try {
        return JSON.parse(localStorage.getItem("forms_pro_collapsed_categories") || "{}");
    } catch {
        return {};
    }
}

function toggle(label: string) {
    collapsed.value[label] = !collapsed.value[label];
    try {
        localStorage.setItem(
            "forms_pro_collapsed_categories",
            JSON.stringify(collapsed.value)
        );
    } catch {
        /* private mode — collapsing just won't persist */
    }
}

// SortableJS mutates the bound list, so hand each group its own array.
function listFor(fields: FormFields[]) {
    return [...fields];
}

function cloneField(f: FormFields) {
    return { __newFieldtype: f.name, label: f.name };
}
</script>

<template>
    <div class="flex flex-col gap-3">
        <div class="flex flex-col gap-1">
            <h3 class="text-sm-semibold text-ink-gray-8">Add Fields</h3>
            <p class="text-xs text-ink-gray-5">
                Drag a field onto the canvas, or click to append it.
            </p>
        </div>

        <FormControl
            v-model="search"
            type="search"
            variant="outline"
            size="sm"
            placeholder="Search fields"
        />

        <!-- Flat list while searching -->
        <draggableComponent
            v-if="hasSearch"
            :list="listFor(searchResults)"
            :group="{ name: 'fields', pull: 'clone', put: false }"
            :sort="false"
            :clone="cloneField"
            item-key="name"
            tag="div"
            :force-fallback="true"
            :fallback-on-body="true"
            :fallback-tolerance="4"
            :animation="150"
            ghost-class="fp-drag-ghost"
            drag-class="fp-drag-preview"
            class="flex flex-col gap-1"
            @start="editFormStore.setDragging(true)"
            @end="editFormStore.setDragging(false)"
        >
            <template #item="{ element: field }">
                <button
                    type="button"
                    class="flex w-full items-center gap-2.5 px-3 py-2 bg-surface-gray-1/70 rounded-lg border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-white hover:shadow-2xs active:scale-[0.98] cursor-grab active:cursor-grabbing focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 transition-all duration-150 text-left"
                    @click="editFormStore.addField(field.name)"
                >
                    <component :is="field.icon" class="w-4 h-4 text-ink-gray-6 shrink-0" aria-hidden="true" />
                    <span class="text-sm font-medium text-ink-gray-8 truncate">{{ field.name }}</span>
                </button>
            </template>
        </draggableComponent>

        <p v-if="hasSearch && searchResults.length === 0" class="text-xs text-ink-gray-5 text-center py-4">
            No fields match "{{ search }}"
        </p>

        <!-- Collapsible categories -->
        <template v-else>
            <div v-for="group in groups" :key="group.label" class="flex flex-col gap-1.5">
                <button
                    type="button"
                    class="flex items-center gap-1 px-1 text-xs font-semibold uppercase tracking-wider text-ink-gray-5 hover:text-ink-gray-7 transition-colors"
                    :aria-expanded="!collapsed[group.label]"
                    @click="toggle(group.label)"
                >
                    <ChevronRight
                        class="w-3 h-3 transition-transform duration-150 motion-reduce:transition-none"
                        :class="collapsed[group.label] ? '' : 'rotate-90'"
                        aria-hidden="true"
                    />
                    {{ group.label }}
                </button>

                <draggableComponent
                    v-show="!collapsed[group.label]"
                    :list="listFor(group.fields)"
                    :group="{ name: 'fields', pull: 'clone', put: false }"
                    :sort="false"
                    :clone="cloneField"
                    item-key="name"
                    tag="div"
                    :force-fallback="true"
                    :animation="200"
                    ghost-class="opacity-50"
                    class="flex flex-col gap-1"
                    @start="editFormStore.setDragging(true)"
                    @end="editFormStore.setDragging(false)"
                >
                    <template #item="{ element: field }">
                        <button
                            type="button"
                            class="flex w-full items-center gap-2.5 px-3 py-2 bg-surface-gray-1/70 rounded-lg border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-white hover:shadow-2xs active:scale-[0.98] cursor-grab active:cursor-grabbing focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 transition-all duration-150 text-left"
                            @click="editFormStore.addField(field.name)"
                        >
                            <component :is="field.icon" class="w-4 h-4 text-ink-gray-6 shrink-0" aria-hidden="true" />
                            <span class="text-sm font-medium text-ink-gray-8 truncate">{{ field.name }}</span>
                        </button>
                    </template>
                </draggableComponent>
            </div>
        </template>
    </div>
</template>
