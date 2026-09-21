<script setup lang="ts">
import { ref, computed } from "vue";
import { Dialog, Button, Tooltip } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import FieldRenderer from "@/components/builder/FieldRenderer.vue";
import Heading from "@/components/fields/Heading.vue";
import PageBreak from "@/components/fields/PageBreak.vue";
import { useGroupedRows } from "@/composables/useGroupedRows";
import SuccessCanvas from "@/components/studio/success/SuccessCanvas.vue";
import { Monitor, Tablet, Smartphone, RotateCw } from "@lucide/vue";

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: "close"): void }>();

const editFormStore = useEditForm();

const MODES = [
  { key: "desktop", label: "Desktop", icon: Monitor, width: "100%" },
  { key: "tablet", label: "Tablet", icon: Tablet, width: "768px" },
  { key: "mobile", label: "Mobile", icon: Smartphone, width: "375px" },
] as const;

const mode = ref<(typeof MODES)[number]>(MODES[0]);
const previewTab = ref<"form" | "success">("form");
const isLandscape = ref(false);

const previewWidth = computed(() => isLandscape.value ? "auto" : mode.value.width);
const previewMaxWidth = computed(() => isLandscape.value ? mode.value.width : "100%");

const { rows } = useGroupedRows(
  computed(() => editFormStore.fields),
  computed(() => []),
);

function isHeading(field: any): boolean {
  return ["Heading 1", "Heading 2", "Heading 3"].includes(field.fieldtype);
}

function isPageBreak(field: any): boolean {
  return field.fieldtype === "Page Break";
}

function close() {
  emit("close");
}

const formData = computed(() => editFormStore.formData);
</script>

<template>
  <Dialog :open="show" @close="close" size="7xl" :dismissible="true">
    <template #title>
      <div class="flex items-center justify-between w-full">
        <span class="text-lg-semibold text-ink-gray-9">Preview</span>
        <Tooltip text="Rotate" placement="bottom">
          <Button variant="ghost" size="sm" :icon="RotateCw" @click="isLandscape = !isLandscape" />
        </Tooltip>
      </div>
    </template>
    <template #body-main>
      <div class="flex flex-col gap-6 min-h-[640px]">
        <!-- Mode selector -->
        <div class="flex items-center justify-center gap-2.5">
          <Button
            v-for="m in MODES"
            :key="m.key"
            :variant="mode.key === m.key ? 'subtle' : 'ghost'"
            :theme="mode.key === m.key ? 'gray' : 'gray'"
            size="sm"
            @click="mode = m"
            :disabled="isLandscape"
            :icon-left="m.icon"
            :label="m.label"
          />
        </div>

        <!-- Tab selector -->
        <div class="flex justify-center gap-3 border-b border-outline-gray-1 -mb-px">
          <button
            class="px-5 py-3 text-sm-medium rounded-t-4 border-b-2 -mb-px transition-base active:scale-98"
            :class="previewTab === 'form' 
              ? 'text-ink-gray-9 border-surface-gray-9 bg-surface-gray-1' 
              : 'text-ink-gray-6 border-transparent hover:text-ink-gray-8 hover:bg-surface-gray-2 active:bg-surface-gray-3'"
            @click="previewTab = 'form'"
          >
            Form
          </button>
          <button
            class="px-5 py-3 text-sm-medium rounded-t-4 border-b-2 -mb-px transition-base active:scale-98"
            :class="previewTab === 'success' 
              ? 'text-ink-gray-9 border-surface-gray-9 bg-surface-gray-1' 
              : 'text-ink-gray-6 border-transparent hover:text-ink-gray-8 hover:bg-surface-gray-2 active:bg-surface-gray-3'"
            @click="previewTab = 'success'"
          >
            Success Page
          </button>
        </div>

        <!-- Preview canvas -->
        <div class="flex justify-center flex-1 min-h-0 px-6">
          <div
            class="border border-outline-gray-1 rounded-6 bg-surface-base overflow-auto shadow-xl preview-canvas"
            :style="{ width: previewWidth, maxWidth: previewMaxWidth }"
          >
            <!-- Desktop/Tablet frame -->
            <div v-if="!isLandscape && mode.key !== 'mobile'" class="relative">
              <div class="mx-auto bg-surface-gray-9 rounded-6 border border-outline-gray-2 shadow-xl">
                <div class="flex items-center justify-between px-5 h-11 bg-surface-gray-8 rounded-t-6 border-b border-outline-gray-2">
                  <div class="flex gap-2.5">
                    <div class="size-3 rounded-full bg-surface-red-7" aria-hidden="true" />
                    <div class="size-3 rounded-full bg-surface-amber-7" aria-hidden="true" />
                    <div class="size-3 rounded-full bg-surface-green-7" aria-hidden="true" />
                  </div>
                  <div class="text-xs text-ink-gray-4 font-mono">{{ mode.label }} Preview</div>
                  <div class="flex gap-2.5">
                    <div class="size-3 rounded-full bg-surface-gray-6" aria-hidden="true" />
                    <div class="size-3 rounded-full bg-surface-gray-6" aria-hidden="true" />
                    <div class="size-3 rounded-full bg-surface-gray-6" aria-hidden="true" />
                  </div>
                </div>
                <div class="p-8 bg-surface-base rounded-b-6 min-h-[480px]">
                  <!-- Form preview -->
                  <div v-if="previewTab === 'form'" class="space-y-5">
                    <template v-for="(row, rowIdx) in rows" :key="rowIdx">
                      <template v-for="field in row" :key="field.name">
                        <Heading v-if="isHeading(field)" :field="field" />
                        <PageBreak v-else-if="isPageBreak(field)" />
                        <FieldRenderer v-else :field="field" />
                      </template>
                    </template>
                  </div>
                  <!-- Success page preview -->
                  <SuccessCanvas v-else-if="previewTab === 'success' && formData" :form="formData" />
                </div>
              </div>
            </div>
            <!-- Mobile/Landscape view -->
            <div v-else class="p-8 bg-surface-base rounded-6 border border-outline-gray-1 min-h-[480px]">
              <!-- Form preview -->
              <div v-if="previewTab === 'form'" class="space-y-5">
                <template v-for="(row, rowIdx) in rows" :key="rowIdx">
                  <template v-for="field in row" :key="field.name">
                    <Heading v-if="isHeading(field)" :field="field" />
                    <PageBreak v-else-if="isPageBreak(field)" />
                    <FieldRenderer v-else :field="field" />
                  </template>
                </template>
              </div>
              <!-- Success page preview -->
              <SuccessCanvas v-else-if="previewTab === 'success' && formData" :form="formData" />
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

@media (prefers-reduced-motion: reduce) {
  .preview-canvas,
  .transition-base {
    transition: none !important;
  }
}
</style>
