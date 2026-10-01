<script setup lang="ts">
import { useSubmissionForm } from "@/stores/submissionForm";
import { LoadingIndicator, TextEditor } from "frappe-ui";

const store = useSubmissionForm();

/** An editor left empty still saves `<p></p>`; that is no description. */
function hasContent(html?: string | null): boolean {
    if (!html) return false;
    if (/<(img|video|iframe|audio|table|hr)\b/i.test(html)) return true;
    return html.replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").trim().length > 0;
}
</script>
<template>
    <div v-if="!store.formResource">
        <LoadingIndicator />
    </div>

    <!-- Step 2+ compact header (multi-step only), with this step's own description -->
    <div
        v-else-if="store.isMultiStep && !store.isFirstStep && store.formResource.data"
        class="flex flex-col gap-3 pb-4 border-b border-outline-gray-1"
    >
        <div class="flex items-center gap-3">
            <button
                @click="store.prevStep"
                class="flex items-center justify-center w-[30px] h-[30px] shrink-0 rounded-lg border border-outline-gray-2 bg-surface-white text-ink-gray-4 hover:border-outline-gray-4 active:scale-95 transition-[border-color,transform] duration-150 cursor-pointer"
            >
                <lucide-arrow-left class="w-3 h-3" aria-hidden="true" />
            </button>
            <!--
                The form's own title stays on every step. Showing only the
                step's name here made the form look as if it had been renamed
                whenever the visitor moved on.
            -->
            <div class="flex-1 min-w-0">
                <div class="text-[10.5px] text-ink-gray-4 font-medium tracking-wider uppercase mb-0.5 truncate">
                    {{ store.formResource.data.title }} · Step {{ store.currentStepIndex + 1 }} of
                    {{ store.totalSteps }}
                </div>
                <h2 class="text-2xl font-bold text-ink-gray-9 tracking-tight break-words">
                    {{ store.steps[store.currentStepIndex]?.label || `Step ${store.currentStepIndex + 1}` }}
                </h2>
            </div>
            <div
                class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-gray-2 text-[11px] font-semibold text-ink-gray-5 tabular-nums shrink-0"
            >
                {{ store.currentStepFields.length }}
                field{{ store.currentStepFields.length !== 1 ? "s" : "" }}
            </div>
        </div>
        <TextEditor
            v-if="hasContent(store.steps[store.currentStepIndex]?.description)"
            :key="`step-description-${store.currentStepIndex}`"
            :content="store.steps[store.currentStepIndex]?.description"
            editor-class="h-fit !w-full form-description !px-0 max-w-full max-h-full text-ink-gray-7"
            :editable="false"
        />
    </div>

    <!-- Default full header (step 1 or single-step) -->
    <div v-else-if="store.formResource.data" class="flex flex-col gap-4 text-ink-gray-8">
        <h1 class="text-3xl font-bold">
            {{ store.formResource.data.title }}
        </h1>
        <!-- The first step's own heading, as every later step has one. -->
        <h2
            v-if="store.isMultiStep"
            class="text-2xl font-bold text-ink-gray-9 tracking-tight break-words -mt-2"
        >
            {{ store.steps[0]?.label || "Step 1" }}
        </h2>
        <TextEditor
            :content="store.formResource.data?.description"
            editor-class="h-fit !w-full form-description !px-0 max-w-full max-h-full"
            :editable="false"
        />
        <hr />
    </div>
</template>
