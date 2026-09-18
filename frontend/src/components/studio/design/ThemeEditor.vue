<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { Button, FormControl, Tooltip, Badge } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import { Palette, Type, PaintBucket, Ruler, Square, Save, FolderOpen, AlertTriangle, Eye, Contrast } from "@lucide/vue";

const editFormStore = useEditForm();

interface ThemeTokens {
  font_family: string;
  font_size: string;
  text_color: string;
  muted_text_color: string;
  background_color: string;
  primary_color: string;
  primary_hover_color: string;
  input_border_color: string;
  input_focus_color: string;
  input_radius: string;
  button_radius: string;
  card_radius: string;
  form_max_width: string;
  field_gap: string;
}

const defaults: ThemeTokens = {
  font_family: "Inter",
  font_size: "16px",
  text_color: "#111827",
  muted_text_color: "#6B7280",
  background_color: "#FFFFFF",
  primary_color: "#1D4ED8",
  primary_hover_color: "#1E40AF",
  input_border_color: "#D1D5DB",
  input_focus_color: "#2563EB",
  input_radius: "8px",
  button_radius: "8px",
  card_radius: "12px",
  form_max_width: "720px",
  field_gap: "16px",
};

const tokens = ref<ThemeTokens>({ ...defaults });

watch(() => editFormStore.formData, (data) => {
  if (data?.theme_overrides_json) {
    try {
      tokens.value = { ...defaults, ...JSON.parse(data.theme_overrides_json) };
    } catch {
      tokens.value = { ...defaults };
    }
  }
}, { immediate: true });

watch(tokens, () => {
  if (editFormStore.formResource?.doc) {
    editFormStore.formResource.doc.theme_overrides_json = JSON.stringify(tokens.value);
  }
}, { deep: true });

const sections = [
  {
    label: "Typography",
    icon: Type,
    fields: [
      { key: "font_family" as const, label: "Font Family", type: "select", options: ["Inter", "Roboto", "Open Sans", "Poppins", "Montserrat", "Nunito", "Source Sans Pro"] },
      { key: "font_size" as const, label: "Font Size", type: "select", options: ["14px", "15px", "16px", "17px", "18px", "20px"] },
    ],
  },
  {
    label: "Colors",
    icon: PaintBucket,
    fields: [
      { key: "text_color" as const, label: "Text", type: "color" },
      { key: "muted_text_color" as const, label: "Muted Text", type: "color" },
      { key: "background_color" as const, label: "Background", type: "color" },
      { key: "primary_color" as const, label: "Primary", type: "color" },
      { key: "primary_hover_color" as const, label: "Primary Hover", type: "color" },
      { key: "input_border_color" as const, label: "Input Border", type: "color" },
      { key: "input_focus_color" as const, label: "Input Focus", type: "color" },
    ],
  },
  {
    label: "Shape & Spacing",
    icon: Ruler,
    fields: [
      { key: "input_radius" as const, label: "Input Radius", type: "select", options: ["4px", "6px", "8px", "10px", "12px", "16px", "24px", "9999px"] },
      { key: "button_radius" as const, label: "Button Radius", type: "select", options: ["4px", "6px", "8px", "10px", "12px", "16px", "24px", "9999px"] },
      { key: "card_radius" as const, label: "Card Radius", type: "select", options: ["8px", "10px", "12px", "16px", "20px", "24px"] },
      { key: "form_max_width" as const, label: "Max Width", type: "select", options: ["640px", "720px", "800px", "960px", "1024px", "1200px"] },
      { key: "field_gap" as const, label: "Field Gap", type: "select", options: ["8px", "12px", "16px", "20px", "24px", "32px"] },
    ],
  },
];

function resetTheme() {
  tokens.value = { ...defaults };
}

function saveTheme() {
  const theme = {
    name: `Custom Theme ${new Date().toLocaleDateString()}`,
    tokens: tokens.value,
    created_at: new Date().toISOString(),
  };
  const existing = JSON.parse(localStorage.getItem("forms_pro_themes") || "[]");
  existing.push(theme);
  localStorage.setItem("forms_pro_themes", JSON.stringify(existing));
  (window as any).frappe?.show_alert?.({ message: "Theme saved", indicator: "green" });
}

function loadTheme(theme: any) {
  tokens.value = { ...defaults, ...theme.tokens };
  (window as any).frappe?.show_alert?.({ message: "Theme loaded", indicator: "green" });
}

const savedThemes = computed(() => {
  try {
    return JSON.parse(localStorage.getItem("forms_pro_themes") || "[]");
  } catch {
    return [];
  }
});

function deleteTheme(index: number) {
  const themes = savedThemes.value;
  themes.splice(index, 1);
  localStorage.setItem("forms_pro_themes", JSON.stringify(themes));
}

// Contrast ratio calculation (WCAG)
function getLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0;
  const [r, g, b] = [rgb.r, rgb.g, rgb.b].map(v => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = hex.replace("#", "").match(hex.length === 4 ? /([0-9a-f])/gi : /([0-9a-f]{2})/gi);
  if (!m) return null;
  return {
    r: parseInt(m[0] + (m[0].length === 1 ? m[0] : ""), 16),
    g: parseInt(m[1] + (m[1].length === 1 ? m[1] : ""), 16),
    b: parseInt(m[2] + (m[2].length === 1 ? m[2] : ""), 16),
  };
}

function getContrastRatio(color1: string, color2: string): number {
  const l1 = getLuminance(color1);
  const l2 = getLuminance(color2);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

const contrastWarnings = computed(() => {
  const warnings: { label: string; ratio: number; level: "AA" | "AAA" | "fail" }[] = [];
  const bg = tokens.value.background_color;
  const text = tokens.value.text_color;
  const muted = tokens.value.muted_text_color;
  const primary = tokens.value.primary_color;
  
  const textRatio = getContrastRatio(text, bg);
  const mutedRatio = getContrastRatio(muted, bg);
  const primaryRatio = getContrastRatio(primary, bg);
  
  const check = (label: string, ratio: number) => {
    let level: "AA" | "AAA" | "fail" = "fail";
    if (ratio >= 7) level = "AAA";
    else if (ratio >= 4.5) level = "AA";
    warnings.push({ label, ratio: Math.round(ratio * 10) / 10, level });
  };
  
  check("Text on Background", textRatio);
  check("Muted Text on Background", mutedRatio);
  check("Primary on Background", primaryRatio);
  check("Primary on White", getContrastRatio(primary, "#FFFFFF"));
  
  return warnings;
});

function exportTheme() {
  const theme = {
    name: "Custom Theme",
    tokens: tokens.value,
    exported_at: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(theme, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "forms-pro-theme.json";
  a.click();
  URL.revokeObjectURL(url);
}

function importTheme(file: File) {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const theme = JSON.parse(e.target?.result as string);
      if (theme.tokens) {
        tokens.value = { ...defaults, ...theme.tokens };
        (window as any).frappe?.show_alert?.({ message: "Theme imported", indicator: "green" });
      }
    } catch {
      (window as any).frappe?.show_alert?.({ message: "Invalid theme file", indicator: "red" });
    }
  };
  reader.readAsText(file);
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <!-- Left: Settings -->
    <div class="w-72 border-r bg-white p-4 overflow-y-auto flex flex-col gap-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-base font-semibold text-gray-800">Theme</h2>
          <p class="text-xs text-gray-500">Customize form appearance</p>
        </div>
        <div class="flex gap-1">
          <Tooltip text="Save Theme" placement="bottom">
            <Button variant="ghost" size="sm" @click="saveTheme"><Save class="w-3.5 h-3.5" /></Button>
          </Tooltip>
          <Tooltip text="Export Theme" placement="bottom">
            <Button variant="ghost" size="sm" @click="exportTheme"><FolderOpen class="w-3.5 h-3.5" /></Button>
          </Tooltip>
          <Tooltip text="Reset to Defaults" placement="bottom">
            <Button variant="ghost" size="sm" @click="resetTheme"><Eye class="w-3.5 h-3.5" /></Button>
          </Tooltip>
        </div>
      </div>

      <!-- Saved Themes -->
      <div v-if="savedThemes.length" class="flex flex-col gap-2 p-3 bg-gray-50 rounded-lg">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-gray-500 uppercase">Saved Themes</span>
          <input type="file" accept=".json" @change="importTheme($event.target.files[0])" class="hidden" ref="fileInput" />
          <Button variant="ghost" size="sm" @click="$refs.fileInput?.click()"><Contrast class="w-3.5 h-3.5" /></Button>
        </div>
        <div class="flex flex-wrap gap-1">
          <button
            v-for="(theme, i) in savedThemes"
            :key="theme.name + i"
            class="text-xs px-2 py-1 bg-white rounded border hover:bg-gray-50 flex items-center gap-1"
            @click="loadTheme(theme)"
          >
            <span>{{ theme.name }}</span>
            <button @click.stop="deleteTheme(i)" class="text-red-500 hover:text-red-700 text-xs">×</button>
          </button>
        </div>
      </div>

      <!-- Contrast Warnings -->
      <div v-if="contrastWarnings.some(w => w.level === 'fail')" class="p-3 bg-red-50 border border-red-200 rounded-lg">
        <div class="flex items-center gap-2 text-xs text-red-700 mb-2">
          <AlertTriangle class="w-4 h-4" />
          <span class="font-medium">Contrast Issues</span>
        </div>
        <div class="flex flex-col gap-1 text-xs">
          <div v-for="w in contrastWarnings" :key="w.label" class="flex justify-between">
            <span class="text-gray-600">{{ w.label }}</span>
            <Badge :variant="w.level === 'fail' ? 'solid' : 'subtle'" :theme="w.level === 'AAA' ? 'green' : w.level === 'AA' ? 'blue' : 'red'" :label="w.ratio + ':1'" />
          </div>
          <p class="text-xs text-red-600 mt-1">WCAG AA requires 4.5:1 for text, 3:1 for large text</p>
        </div>
      </div>

      <!-- Theme Settings -->
      <div v-for="section in sections" :key="section.label" class="flex flex-col gap-3">
        <div class="flex items-center gap-2 pt-2 border-t">
          <component :is="section.icon" class="w-4 h-4 text-gray-400" />
          <span class="text-xs font-semibold text-gray-500 uppercase">{{ section.label }}</span>
        </div>
        <div v-for="field in section.fields" :key="field.key" class="flex items-center gap-2">
          <label class="text-xs text-gray-500 w-28 shrink-0">{{ field.label }}</label>
          <div v-if="field.type === 'color'" class="flex items-center gap-2">
            <input
              type="color"
              :value="tokens[field.key]"
              @input="(e: any) => tokens[field.key] = e.target.value"
              class="w-8 h-8 rounded border border-gray-200 cursor-pointer p-0 overflow-hidden"
            />
          </div>
          <FormControl
            v-else
            type="select"
            variant="outline"
            size="sm"
            :options="field.options"
            v-model="tokens[field.key]"
          />
        </div>
      </div>
    </div>

    <!-- Right: Live preview -->
    <div class="flex-1 p-6 overflow-auto flex justify-center">
      <div
        class="w-full rounded-lg border shadow-sm p-6 transition-all"
        :style="{
          maxWidth: tokens.form_max_width,
          backgroundColor: tokens.background_color,
          fontFamily: tokens.font_family,
          fontSize: tokens.font_size,
          color: tokens.text_color,
          gap: tokens.field_gap,
        }"
      >
        <p class="text-xs mb-2" :style="{ color: tokens.muted_text_color }">Live Preview</p>

        <!-- Sample field -->
        <div class="flex flex-col gap-1">
          <label class="text-sm font-medium">Sample Label</label>
          <input
            class="w-full border rounded px-3 py-2 text-sm transition-colors"
            :style="{
              borderColor: tokens.input_border_color,
              borderRadius: tokens.input_radius,
            }"
            :onfocus="(e: any) => { e.target.style.borderColor = tokens.input_focus_color; e.target.style.outline = 'none'; e.target.style.boxShadow = '0 0 0 2px ' + tokens.input_focus_color + '33'; }"
            placeholder="Sample input..."
            readonly
          />
        </div>

        <!-- Sample button -->
        <button
          class="px-4 py-2 text-white text-sm font-medium mt-4 transition-colors"
          :style="{
            backgroundColor: tokens.primary_color,
            borderRadius: tokens.button_radius,
          }"
          @mouseenter="(e: any) => e.target.style.backgroundColor = tokens.primary_hover_color"
          @mouseleave="(e: any) => e.target.style.backgroundColor = tokens.primary_color"
        >
          Submit
        </button>

        <!-- Sample card -->
        <div
          class="mt-4 p-4 border text-sm"
          :style="{
            borderRadius: tokens.card_radius,
            borderColor: tokens.input_border_color,
            color: tokens.muted_text_color,
          }"
        >
          Sample card with {{ tokens.card_radius }} radius
        </div>

        <!-- Contrast ratios display -->
        <div class="mt-4 pt-4 border-t text-xs" :style="{ borderColor: tokens.input_border_color }">
          <div class="font-medium mb-2" :style="{ color: tokens.text_color }">Contrast Ratios</div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div v-for="w in contrastWarnings" :key="w.label" class="flex justify-between">
              <span :style="{ color: tokens.muted_text_color }">{{ w.label }}</span>
              <span class="font-medium" :style="{ color: w.level === 'fail' ? '#ef4444' : w.level === 'AAA' ? '#16a34a' : '#2563eb' }">{{ w.ratio }}:1</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>