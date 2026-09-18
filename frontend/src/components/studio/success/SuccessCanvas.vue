<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { Button, FormControl } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import {
  Plus,
  Trash2,
  MoveUp,
  MoveDown,
  AlignLeft,
  Type,
  Image,
  SeparatorHorizontal,
  GripVertical,
  Link2,
  ListChecks,
  ArrowRight,
  Copy,
} from "@lucide/vue";

const editFormStore = useEditForm();

interface SuccessBlock {
  id: string;
  type: "icon" | "heading" | "paragraph" | "image" | "divider" | "spacer" | "button" | "reference" | "summary" | "steps";
  content: string;
  style: Record<string, string>;
}

const blocks = ref<SuccessBlock[]>([]);
const selectedId = ref<string | null>(null);
const dragOverId = ref<string | null>(null);
const draggedId = ref<string | null>(null);

const blockTypes = [
  { type: "icon" as const, label: "Icon", icon: "✓" },
  { type: "heading" as const, label: "Heading", icon: Type },
  { type: "paragraph" as const, label: "Text", icon: AlignLeft },
  { type: "image" as const, label: "Image", icon: Image },
  { type: "divider" as const, label: "Divider", icon: SeparatorHorizontal },
  { type: "spacer" as const, label: "Spacer", icon: "⏎" },
  { type: "button" as const, label: "Button", icon: "→" },
  { type: "reference" as const, label: "Submission Ref", icon: Link2 },
  { type: "summary" as const, label: "Response Summary", icon: ListChecks },
  { type: "steps" as const, label: "Next Steps", icon: ArrowRight },
] as const;

const mergeTags = ["{{ submission_id }}", "{{ form_title }}"];

function addBlock(type: SuccessBlock["type"]) {
  const id = "block_" + Math.random().toString(36).slice(2, 9);
  const defaults: Record<string, string> = {
    icon: "✓",
    heading: "Thank you!",
    paragraph: "Your response has been recorded.",
    image: "",
    divider: "",
    spacer: "",
    button: "Back to website",
    reference: "{{ submission_id }}",
    summary: "Submitted fields: {{ fields }}",
    steps: "1. Check your email\n2. We'll contact you within 24h",
  };

  blocks.value.push({
    id,
    type,
    content: defaults[type] || "",
    style: {},
  });
  selectedId.value = id;
}

function removeBlock(id: string) {
  blocks.value = blocks.value.filter((b) => b.id !== id);
  if (selectedId.value === id) selectedId.value = null;
}

function moveBlock(id: string, dir: -1 | 1) {
  const idx = blocks.value.findIndex((b) => b.id === id);
  if (idx === -1) return;
  const newIdx = idx + dir;
  if (newIdx < 0 || newIdx >= blocks.value.length) return;
  const tmp = blocks.value[idx];
  blocks.value[idx] = blocks.value[newIdx];
  blocks.value[newIdx] = tmp;
}

// Drag and drop handlers
function onDragStart(id: string) {
  draggedId.value = id;
  selectedId.value = id;
}

function onDragOver(id: string, e: DragEvent) {
  e.preventDefault();
  dragOverId.value = id;
}

function onDragLeave() {
  dragOverId.value = null;
}

function onDrop(id: string, e: DragEvent) {
  e.preventDefault();
  if (!draggedId.value || draggedId.value === id) return;
  
  const fromIdx = blocks.value.findIndex((b) => b.id === draggedId.value);
  const toIdx = blocks.value.findIndex((b) => b.id === id);
  if (fromIdx === -1 || toIdx === -1) return;
  
  const [moved] = blocks.value.splice(fromIdx, 1);
  blocks.value.splice(toIdx, 0, moved);
  
  draggedId.value = null;
  dragOverId.value = null;
}

function onDragEnd() {
  draggedId.value = null;
  dragOverId.value = null;
}

// Persist to form schema
watch(blocks, () => {
  if (editFormStore.formResource?.doc) {
    editFormStore.formResource.doc.success_schema_json = JSON.stringify(blocks.value);
  }
}, { deep: true });

// Load from form
watch(() => editFormStore.formData, (data) => {
  if (data?.success_schema_json) {
    try {
      blocks.value = JSON.parse(data.success_schema_json);
    } catch {
      blocks.value = [];
    }
  }
});

const selectedBlock = computed(() => blocks.value.find((b) => b.id === selectedId.value) || null);

  // Insert merge tag at cursor position in textarea
  function insertMergeTag(tag: string) {
    if (!selectedBlock.value || selectedBlock.value.type !== "paragraph") return;
    const textarea = document.querySelector('.block-properties textarea') as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const value = selectedBlock.value.content;
      selectedBlock.value.content = value.slice(0, start) + tag + value.slice(end);
      nextTick(() => {
        textarea.focus();
        textarea.setSelectionRange(start + tag.length, start + tag.length);
      });
    }
  }
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <!-- Left: Block palette -->
    <div class="w-48 border-r bg-white p-4 flex flex-col gap-3">
      <h3 class="text-sm font-semibold text-gray-600 uppercase tracking-wide">Blocks</h3>
      <button
        v-for="bt in blockTypes"
        :key="bt.type"
        class="flex items-center gap-2 px-2 py-1.5 text-sm rounded hover:bg-gray-100 transition-colors text-left text-gray-700 w-full"
        @click="addBlock(bt.type)"
      >
        <span class="w-5 h-5 flex items-center justify-center text-gray-500 text-xs">
          <component v-if="typeof bt.icon !== 'string'" :is="bt.icon" class="w-4 h-4" />
          <span v-else>{{ bt.icon }}</span>
        </span>
        {{ bt.label }}
      </button>
    </div>

    <!-- Center: Canvas -->
    <div class="flex-1 overflow-auto p-6">
      <div class="max-w-lg mx-auto bg-white rounded border border-gray-200 shadow-sm min-h-[400px] p-6 flex flex-col items-center gap-3">
        <template v-if="blocks.length === 0">
          <p class="text-sm text-gray-400 py-20">Add blocks to design your success page</p>
        </template>
        <template v-for="block in blocks" :key="block.id">
          <div
            class="w-full cursor-pointer rounded p-2 transition-colors relative group"
            :class="[
              selectedId === block.id ? 'ring-2 ring-blue-400 bg-blue-50' : 'hover:bg-gray-50',
              dragOverId === block.id ? 'bg-blue-50 border-l-4 border-blue-400' : ''
            ]"
            @click="selectedId = block.id"
            draggable="true"
            @dragstart="onDragStart(block.id)"
            @dragover="onDragOver(block.id, $event)"
            @dragleave="onDragLeave"
            @drop="onDrop(block.id)"
            @dragend="onDragEnd"
          >
            <!-- Drag handle -->
            <button
              class="absolute -left-8 top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center text-gray-300 hover:text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity"
              @click.stop
              @dragstart="onDragStart(block.id)"
            >
              <GripVertical class="w-4 h-4" />
            </button>

            <!-- Icon -->
            <div v-if="block.type === 'icon'" class="flex justify-center">
              <div class="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-xl font-bold">
                {{ block.content }}
              </div>
            </div>

            <!-- Heading -->
            <h2 v-else-if="block.type === 'heading'" class="text-xl font-semibold text-center">{{ block.content || "Heading" }}</h2>

            <!-- Paragraph -->
            <p v-else-if="block.type === 'paragraph'" class="text-sm text-gray-600 text-center">{{ block.content || "Text" }}</p>

            <!-- Divider -->
            <hr v-else-if="block.type === 'divider'" class="border-gray-200" />

            <!-- Spacer -->
            <div v-else-if="block.type === 'spacer'" class="h-8" />

            <!-- Button -->
            <div v-else-if="block.type === 'button'" class="flex justify-center">
              <span class="px-4 py-2 bg-blue-600 text-white text-sm rounded-md">{{ block.content || "Button" }}</span>
            </div>

            <!-- Reference -->
            <code v-else-if="block.type === 'reference'" class="text-xs bg-gray-100 px-2 py-1 rounded text-center block">{{ block.content }}</code>

            <!-- Summary -->
            <div v-else-if="block.type === 'summary'" class="text-xs bg-gray-50 px-3 py-2 rounded text-center text-gray-600">
              {{ block.content }}
            </div>

            <!-- Steps -->
            <div v-else-if="block.type === 'steps'" class="text-xs text-gray-600 space-y-1">
              <div v-for="(line, i) in block.content.split('\n')" :key="i" class="flex items-center gap-2">
                <span class="w-5 h-5 flex items-center justify-center bg-blue-100 text-blue-600 rounded-full text-xs font-medium">{{ i + 1 }}</span>
                <span>{{ line }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Right: Properties -->
    <div class="w-56 border-l bg-white p-4 flex flex-col gap-3" v-if="selectedBlock">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold">{{ selectedBlock.type }}</h3>
        <div class="flex gap-1">
          <Button variant="ghost" size="sm" @click="moveBlock(selectedBlock.id, -1)" :disabled="blocks[0]?.id === selectedBlock.id">
            <MoveUp class="w-3.5 h-3.5" />
          </Button>
          <Button variant="ghost" size="sm" @click="moveBlock(selectedBlock.id, 1)" :disabled="blocks[blocks.length - 1]?.id === selectedBlock.id">
            <MoveDown class="w-3.5 h-3.5" />
          </Button>
          <Button variant="ghost" size="sm" theme="red" @click="removeBlock(selectedBlock.id)">
            <Trash2 class="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      <template v-if="['icon', 'heading', 'paragraph', 'button', 'reference', 'summary', 'steps'].includes(selectedBlock.type)">
        <label class="text-xs text-gray-500">Content</label>
        <FormControl
          v-if="selectedBlock.type === 'paragraph' || selectedBlock.type === 'summary' || selectedBlock.type === 'steps'"
          type="textarea"
          variant="outline"
          v-model="selectedBlock.content"
          class="block-properties"
        />
        <FormControl
          v-else
          type="text"
          variant="outline"
          v-model="selectedBlock.content"
        />
      </template>

      <div v-if="selectedBlock.type !== 'spacer' && selectedBlock.type !== 'divider' && selectedBlock.type !== 'image'" class="mt-2">
        <label class="text-xs text-gray-500">Merge Tags</label>
        <div class="flex flex-wrap gap-1 mt-1">
          <button
            v-for="tag in mergeTags"
            :key="tag"
            class="text-xs px-1.5 py-0.5 bg-gray-100 rounded hover:bg-gray-200"
            @click="insertMergeTag(tag)"
            @mousedown.prevent
          >
            {{ tag }}
          </button>
        </div>
      </div>

      <div v-if="selectedBlock.type === 'button'" class="mt-2">
        <label class="text-xs text-gray-500">Action</label>
        <FormControl type="text" variant="outline" size="sm" placeholder="https://example.com" v-model="selectedBlock.style.href" />
      </div>

      <div v-if="selectedBlock.type === 'image'" class="mt-2">
        <label class="text-xs text-gray-500">Image URL</label>
        <FormControl type="text" variant="outline" size="sm" placeholder="https://example.com/image.png" v-model="selectedBlock.content" />
      </div>
    </div>
  </div>
</template>