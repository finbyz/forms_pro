<script setup lang="ts">
import { useRoute } from "vue-router";
import { useSubmissionForm } from "@/stores/submissionForm";
import FormHeader from "@/components/submission/FormHeader.vue";
import FormRenderer from "@/components/submission/FormRenderer.vue";
import StepIndicator from "@/components/submission/StepIndicator.vue";
import Logo from "@/assets/Logo.vue";
import PageHeader from "@/components/submission/PageHeader.vue";
import SuccessSection from "@/components/submission/SuccessSection.vue";

const route = useRoute();
const submissionFormStore = useSubmissionForm();
submissionFormStore.initialize(route.params.route as string);

import { onMounted, onUnmounted, watch } from "vue";

// Embed integration: Resize observer
let resizeObserver: ResizeObserver | null = null;
onMounted(() => {
    if (window !== window.parent) {
        resizeObserver = new ResizeObserver((entries) => {
            const height = entries[0].target.scrollHeight;
            window.parent.postMessage({ type: "formspro:resize", height }, "*");
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
    if (isSuccess && window !== window.parent) {
        window.parent.postMessage({ 
            type: "formspro:submitted", 
            payload: { route: route.params.route } 
        }, "*");
    }
});

</script>
<template>
    <div class="p-8 bg-surface-gray-1 min-h-svh space-y-16">
        <PageHeader />
        <FormUnpublishedState
            v-if="!submissionFormStore.formIsPublished"
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

        <div class="z-10 fixed bottom-0 right-0 p-8">
            <div
                class="flex flex-col items-end text-ink-gray-2 md:text-ink-gray-4 hover:text-ink-gray-8 transition-colors duration-300 mt-4"
            >
                <span class="text-xs">Built on</span>
                <a
                    href="https://github.com/buildwithhussain/forms_pro"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    <Logo class="font-normal" />
                </a>
            </div>
        </div>
    </div>
</template>
