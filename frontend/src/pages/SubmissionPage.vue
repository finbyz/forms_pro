<script setup lang="ts">
import { useRoute } from "vue-router";
import { useSubmissionForm } from "@/stores/submissionForm";
import FormHeader from "@/components/submission/FormHeader.vue";
import FormRenderer from "@/components/submission/FormRenderer.vue";
import StepIndicator from "@/components/submission/StepIndicator.vue";
import { LoadingIndicator } from "frappe-ui";
import PageHeader from "@/components/submission/PageHeader.vue";
import SuccessSection from "@/components/submission/SuccessSection.vue";
import BuiltByBadge from "@/components/submission/BuiltByBadge.vue";
import { applyTheme } from "@/utils/formTheme";

const route = useRoute();
const submissionFormStore = useSubmissionForm();
submissionFormStore.initialize(route.params.route as string);

import { onMounted, onUnmounted, ref, watch } from "vue";

// The published theme, applied only when the form actually carries one.
const themeRoot = ref<HTMLElement | null>(null);
watch(
    () => [themeRoot.value, submissionFormStore.formResource?.data?.theme_overrides_json] as const,
    ([el, raw]) => applyTheme(el as HTMLElement | null, raw),
    { immediate: true }
);


/**
 * Messages to the embedding page.
 *
 * The host loader only acts on messages carrying `source: "forms-pro"` and
 * reads the name off `event`. This page was sending neither -- no `source` at
 * all, and `type` instead of `event` -- so every message was ignored: the
 * iframe never auto-resized and the `formspro_form_submit` dataLayer event was
 * never pushed, which is why it could not be found in GTM.
 */
function postToHost(event: string, data: Record<string, unknown> = {}) {
    if (window === window.parent) return;
    window.parent.postMessage({ source: "forms-pro", event, ...data }, "*");
}

// Embed integration: Resize observer
let resizeObserver: ResizeObserver | null = null;
onMounted(() => {
    if (window !== window.parent) {
        resizeObserver = new ResizeObserver((entries) => {
            const height = entries[0].target.scrollHeight;
            postToHost("formspro:resize", { height });
        });
        resizeObserver.observe(document.body);
    }
});

onUnmounted(() => {
    if (resizeObserver) {
        resizeObserver.disconnect();
    }
});

// Embed integration: Submission success event
watch(() => submissionFormStore.inSuccessState, (isSuccess) => {
    if (!isSuccess) return;
    postToHost("formspro:submitted", {
        // Field names the host loader reads when pushing to the dataLayer.
        form: submissionFormStore.formResource?.data?.title ?? route.params.route,
        submission_id: submissionFormStore.lastSubmissionId,
        route: route.params.route,
    });
});

</script>
<template>
    <div ref="themeRoot" class="p-8 bg-surface-gray-1 min-h-svh space-y-16">
        <PageHeader />

        <!-- Loading State: shown while form metadata is being retrieved -->
        <div
            v-if="submissionFormStore.isLoading || submissionFormStore.formIsPublished === null"
            class="form-container-simple flex items-center justify-center py-24 min-h-[300px]"
        >
            <LoadingIndicator class="w-8 h-8 text-ink-gray-4" />
        </div>

        <!-- Unpublished State: strictly shown only when confirmed unpublished -->
        <FormUnpublishedState
            v-else-if="submissionFormStore.formIsPublished === false"
            class="form-container-simple"
        />
        <div v-else>
            <div class="px-8 my-6">
                <StepIndicator
                    v-if="
                        submissionFormStore.isMultiStep && submissionFormStore.inFormFillingState
                    "
                    :steps="submissionFormStore.steps"
                    :currentIndex="submissionFormStore.currentStepIndex"
                    class="mb-4"
                    @go-to="submissionFormStore.goToStep"
                />
            </div>
            <div class="form-container-simple overflow-hidden mb-6">
                <div class="space-y-4" v-if="submissionFormStore.inFormFillingState">
                    <FormHeader />
                    <FormRenderer :disabled="false" />
                </div>
                <SuccessSection v-if="submissionFormStore.inSuccessState" />
            </div>
        </div>

        <BuiltByBadge />
    </div>
</template>
