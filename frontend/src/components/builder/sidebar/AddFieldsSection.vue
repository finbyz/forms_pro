<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { formFields, type FormFields } from "@/utils/form_fields";
import { Fieldtype } from "@/types/FormsPro/form_field.types";
import { FormControl } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";

const search = ref("");

const HIDDEN_FROM_SIDEBAR = new Set<string>([Fieldtype.PAGE_BREAK]);

type Category = {
  label: string;
  fieldNames: Fieldtype[];
};

const CATEGORIES: Category[] = [
  {
    label: "Basic",
    fieldNames: [Fieldtype.DATA, Fieldtype.NUMBER, Fieldtype.EMAIL, Fieldtype.PHONE, Fieldtype.TEXTAREA, Fieldtype.TEXT_EDITOR],
  },
  {
    label: "Choice",
    fieldNames: [Fieldtype.SELECT, Fieldtype.MULTISELECT, Fieldtype.CHECKBOX, Fieldtype.SWITCH, Fieldtype.RATING],
  },
  {
    label: "Date & Time",
    fieldNames: [Fieldtype.DATE, Fieldtype.DATE_TIME, Fieldtype.DATE_RANGE, Fieldtype.TIME_PICKER],
  },
  {
    label: "Upload",
    fieldNames: [Fieldtype.ATTACH],
  },
  {
    label: "Layout",
    fieldNames: [Fieldtype.HEADING_1, Fieldtype.HEADING_2, Fieldtype.HEADING_3],
  },
  {
    label: "Advanced",
    fieldNames: [Fieldtype.LINK, Fieldtype.PASSWORD, Fieldtype.TABLE],
  },
];

// Favorites stored in localStorage
const favorites = ref<string[]>(() => {
  try {
    return JSON.parse(localStorage.getItem("forms_pro_favorite_fields") || "[]");
  } catch {
    return [];
  }
});

function toggleFavorite(fieldName: string) {
  const idx = favorites.value.indexOf(fieldName);
  if (idx === -1) {
    favorites.value.push(fieldName);
  } else {
    favorites.value.splice(idx, 1);
  }
  localStorage.setItem("forms_pro_favorite_fields", JSON.stringify(favorites.value));
}

function isFavorite(fieldName: string) {
  return favorites.value.includes(fieldName);
}

// Recently used - track when fields are added
const recent = ref<string[]>(() => {
  try {
    return JSON.parse(localStorage.getItem("forms_pro_recent_fields") || "[]");
  } catch {
    return [];
  }
});

function addToRecent(fieldName: string) {
  const idx = recent.value.indexOf(fieldName);
  if (idx !== -1) recent.value.splice(idx, 1);
  recent.value.unshift(fieldName);
  if (recent.value.length > 10) recent.value.pop();
  localStorage.setItem("forms_pro_recent_fields", JSON.stringify(recent.value));
}

const categorizedFields = computed(() => {
  const q = search.value.toLowerCase();

  const filtered = formFields.filter((f: FormFields) => !HIDDEN_FROM_SIDEBAR.has(f.name));

  if (q) {
    return filtered.filter((f: FormFields) => f.name.toLowerCase().includes(q));
  }

  const result: { category: string; fields: FormFields[] }[] = [];
  for (const cat of CATEGORIES) {
    const items = filtered.filter((f: FormFields) => cat.fieldNames.includes(f.name as Fieldtype));
    if (items.length > 0) {
      result.push({ category: cat.label, fields: items });
    }
  }
  return result;
});

const hasSearch = computed(() => search.value.length > 0);

const favoriteFields = computed(() => {
  return formFields.filter((f: FormFields) => favorites.value.includes(f.name));
});

const recentFields = computed(() => {
  return formFields.filter((f: FormFields) => recent.value.includes(f.name));
});

const editFormStore = useEditForm();
</script>

<template>
    <div class="space-y-4">
        <div class="flex items-center gap-2">
            <h3 class="text-lg font-medium">Add Fields</h3>
            <div class="flex-1"></div>
            <div class="flex items-center gap-1">
                <span class="lucide-search w-4 h-4 text-gray-400" aria-hidden="true" />
                <FormControl
                    v-model="search"
                    type="search"
                    variant="outline"
                    placeholder="Search Fields"
                    class="w-48"
                />
                <button v-if="search" @click="search = ''" class="text-gray-400 hover:text-gray-600" @click.stop>
                    <span class="lucide-x w-4 h-4" aria-hidden="true" />
                </button>
            </div>
        </div>

        <div class="flex flex-col gap-3">
            <!-- Favorites -->
            <div v-if="favoriteFields.length" class="flex flex-col gap-1.5">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1 flex items-center gap-1">
                        <span class="lucide-star w-3 h-3 text-yellow-500" aria-hidden="true" />
                        Favorites
                    </span>
                </div>
                <div class="flex flex-col gap-1">
                    <button
                        v-for="field in favoriteFields"
                        :key="field.name"
                        type="button"
                        class="flex w-full items-center gap-2 px-2.5 py-2 bg-surface-gray-1 rounded border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-gray-2 active:scale-[0.98] active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:ring-offset-1 transition-all duration-150 text-left"
                        @click="() => { editFormStore.addField(field.name); addToRecent(field.name); }"
                    >
                        <component :is="field.icon" class="w-4 h-4 text-gray-600 shrink-0" aria-hidden="true" />
                        <span class="text-sm truncate">{{ field.name }}</span>
                        <button @click.stop="toggleFavorite(field.name)" class="ml-auto text-yellow-500 hover:text-yellow-700" :class="isFavorite(field.name) ? 'fill-current' : ''">
                            <span class="lucide-star w-3 h-3" aria-hidden="true" />
                        </button>
                    </button>
                </div>
            </div>

            <!-- Recently Used -->
            <div v-if="recentFields.length && !hasSearch" class="flex flex-col gap-1.5">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1 flex items-center gap-1">
                        <span class="lucide-history w-3 h-3 text-gray-400" aria-hidden="true" />
                        Recent
                    </span>
                </div>
                <div class="flex flex-col gap-1">
                    <button
                        v-for="field in recentFields"
                        :key="field.name"
                        type="button"
                        class="flex w-full items-center gap-2 px-2.5 py-2 bg-surface-gray-1 rounded border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-gray-2 active:scale-[0.98] active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:ring-offset-1 transition-all duration-150 text-left"
                        @click="() => { editFormStore.addField(field.name); addToRecent(field.name); }"
                    >
                        <component :is="field.icon" class="w-4 h-4 text-gray-600 shrink-0" aria-hidden="true" />
                        <span class="text-sm truncate">{{ field.name }}</span>
                    </button>
                </div>
            </div>

            <p v-if="!hasSearch && (!favoriteFields.length || !recentFields.length) && (!Array.isArray(categorizedFields) || categorizedFields.length === 0)" class="text-sm text-gray-500 px-1 py-2">
                No fields available
            </p>
            <p v-else-if="hasSearch && Array.isArray(categorizedFields) && categorizedFields.length === 0" class="text-sm text-gray-500 px-1 py-2">
                No fields match "{{ search }}"
            </p>

            <!-- Search results: flat list -->
            <div v-if="hasSearch" class="flex flex-col gap-2">
                <div v-if="favoriteFields.length" class="flex flex-col gap-1">
                    <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">
                        <span class="lucide-star w-3 h-3 text-yellow-500" aria-hidden="true" /> Favorites
                    </span>
                    <button
                        v-for="field in favoriteFields"
                        :key="field.name"
                        type="button"
                        class="flex w-full items-center gap-2 px-2.5 py-2 bg-surface-gray-1 rounded border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-gray-2 active:scale-[0.98] active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:ring-offset-1 transition-all duration-150 text-left"
                        @click="() => { editFormStore.addField(field.name); addToRecent(field.name); }"
                    >
                        <component :is="field.icon" class="w-4 h-4 text-gray-600 shrink-0" aria-hidden="true" />
                        <span class="text-sm truncate">{{ field.name }}</span>
                    </button>
                </div>
                <div v-if="recentFields.length" class="flex flex-col gap-1">
                    <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">
                        <span class="lucide-history w-3 h-3 text-gray-400" aria-hidden="true" /> Recent
                    </span>
                    <button
                        v-for="field in recentFields"
                        :key="field.name"
                        type="button"
                        class="flex w-full items-center gap-2 px-2.5 py-2 bg-surface-gray-1 rounded border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-gray-2 active:scale-[0.98] active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:ring-offset-1 transition-all duration-150 text-left"
                        @click="() => { editFormStore.addField(field.name); addToRecent(field.name); }"
                    >
                        <component :is="field.icon" class="w-4 h-4 text-gray-600 shrink-0" aria-hidden="true" />
                        <span class="text-sm truncate">{{ field.name }}</span>
                    </button>
                </div>
                <div class="flex flex-col gap-2">
                    <button
                        v-for="field in categorizedFields.filter(f => !favoriteFields.value.includes(f.name) && !recent.value.includes(f.name))"
                        :key="field.name"
                        type="button"
                        class="flex w-full items-center gap-2 px-2.5 py-2 bg-surface-gray-1 rounded border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-gray-2 active:scale-[0.98] active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:ring-offset-1 transition-all duration-150 text-left"
                        @click="() => { editFormStore.addField(field.name); addToRecent(field.name); }"
                    >
                        <component :is="field.icon" class="w-4 h-4 text-gray-600 shrink-0" aria-hidden="true" />
                        <span class="text-sm truncate">{{ field.name }}</span>
                    </button>
                </div>
            </div>

            <!-- Categorized view -->
            <template v-else>
                <div v-for="cat in categorizedFields" :key="cat.category" class="flex flex-col gap-1.5">
                    <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">{{ cat.category }}</span>
                    <button
                        v-for="field in cat.fields"
                        :key="field.name"
                        type="button"
                        class="flex w-full items-center gap-2 px-2.5 py-2 bg-surface-gray-1 rounded border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-gray-2 active:scale-[0.98] active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:ring-offset-1 transition-all duration-150 text-left"
                        @click="() => { editFormStore.addField(field.name); addToRecent(field.name); }"
                    >
                        <component :is="field.icon" class="w-4 h-4 text-gray-600 shrink-0" aria-hidden="true" />
                        <span class="text-sm truncate">{{ field.name }}</span>
                        <button @click.stop="toggleFavorite(field.name)" class="ml-auto" :class="isFavorite(field.name) ? 'text-yellow-500' : 'text-gray-300 hover:text-yellow-500'">
                            <span class="lucide-star w-3 h-3" aria-hidden="true" />
                        </button>
                    </button>
                </div>
            </template>
        </div>
    </div>
</template>
