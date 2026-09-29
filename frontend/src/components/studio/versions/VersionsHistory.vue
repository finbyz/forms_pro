<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { Button, Badge, createResource } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import { toast } from "vue-sonner";

const editFormStore = useEditForm();
const versions = ref<any[]>([]);
const loading = ref(false);
const reverting = ref<string | null>(null);

const formName = computed(() => editFormStore.originalFormData?.name ?? "");

async function fetchVersions() {
    if (!formName.value) return;
    loading.value = true;
    try {
        const resource = createResource({
            url: "forms_pro.api.v1.builder.data.get_versions",
            makeParams() {
                return { form_name: formName.value };
            },
        });
        await resource.fetch();
        versions.value = resource.data?.versions ?? [];
    } catch (e: any) {
        toast.error(e.message || "Failed to fetch versions");
    } finally {
        loading.value = false;
    }
}

async function doRevert(v: any) {
    if (!confirm(`Revert draft to Version ${v.version_number}? Unsaved changes will be lost.`)) return;
    reverting.value = v.name;
    try {
        const resource = createResource({
            url: "forms_pro.api.v1.builder.data.revert_to_version",
            method: "POST",
            makeParams() {
                return { form_name: formName.value, version_name: v.name };
            },
        });
        await resource.submit();
        // `initialize` returns early for the form already open, so the builder
        // kept showing the draft it had just replaced. Refetch instead.
        editFormStore.reload();
        await editFormStore.refreshPublishState();
        toast.success(`Reverted to v${v.version_number}`);
    } catch (e: any) {
        toast.error(e.message || "Revert failed.");
    } finally {
        reverting.value = null;
    }
}

function fmt(dt: string) { return dt ? new Date(dt).toLocaleString() : "-"; }

onMounted(fetchVersions);
</script>

<template>
    <div class="flex flex-col h-full bg-surface-base">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-5 border-b border-outline-gray-1 bg-surface-base">
            <div>
                <h2 class="text-lg-semibold text-ink-gray-9">Version History</h2>
                <p class="text-sm text-ink-gray-5 mt-1">{{ versions.length }} snapshot{{ versions.length !== 1 ? "s" : "" }}</p>
            </div>
            <Button 
                variant="ghost" 
                icon="refresh-cw" 
                size="sm"
                :loading="loading" 
                @click="fetchVersions"
                aria-label="Refresh versions"
            />
        </div>

        <!-- Content -->
        <div class="flex-1" style="overflow-y: auto">
            <div class="mx-auto max-w-3xl space-y-5 pb-12 px-6 py-6">
                <!-- Empty state -->
                <div v-if="!loading && versions.length === 0" class="flex flex-col items-center py-24 gap-4 text-center">
                    <lucide-git-branch class="w-12 h-12 text-ink-gray-4" aria-hidden="true" />
                    <div>
                        <p class="text-base text-ink-gray-7">No published versions yet</p>
                        <p class="text-sm text-ink-gray-5 mt-1.5">Publish the form to create the first immutable snapshot</p>
                    </div>
                </div>

                <!-- Version list -->
                <div v-for="(v, i) in versions" :key="v.name"
                    class="flex items-start gap-5 bg-surface-base border border-outline-gray-1 rounded-6 p-6 hover:border-outline-gray-2 active:scale-[0.995] transition-base">
                    
                    <!-- Version indicator -->
                    <div class="shrink-0 flex flex-col items-center gap-2.5">
                        <div class="size-10 rounded-full bg-surface-blue-2 border-2 border-outline-blue-3 flex items-center justify-center text-ink-blue-7 text-sm-semibold">
                            v{{ v.version_number }}
                        </div>
                        <div v-if="i < versions.length - 1" class="w-0.5 min-h-[28px] bg-outline-gray-1" aria-hidden="true" />
                    </div>
                    
                    <!-- Version details -->
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2.5 flex-wrap">
                            <span class="text-base-semibold text-ink-gray-9">Version {{ v.version_number }}</span>
                            <Badge v-if="i === 0" label="Latest" theme="blue" variant="subtle" size="sm" />
                        </div>
                        <p class="text-sm text-ink-gray-5 mt-2">
                            {{ fmt(v.published_at) }}
                            <span v-if="v.published_by"> · {{ v.published_by }}</span>
                        </p>
                        <code v-if="v.schema_hash" class="text-xs text-ink-gray-4 font-mono mt-2.5 block">
                            {{ v.schema_hash.slice(0, 12) }}…
                        </code>
                    </div>
                    
                    <!-- Actions -->
                    <Button 
                        v-if="i > 0" 
                        variant="ghost" 
                        size="sm" 
                        icon-left="rotate-ccw"
                        label="Revert"
                        :loading="reverting === v.name" 
                        @click="doRevert(v)"
                    />
                </div>
            </div>
        </div>
    </div>
</template>
