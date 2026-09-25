<script setup lang="ts">
import { Badge, Button, Tooltip } from "frappe-ui";
import { computed } from "vue";
import { useRouter } from "vue-router";
import { toast } from "vue-sonner";
import { ExternalLink, Link2, Pencil, Inbox } from "@lucide/vue";

const props = defineProps<{ form: Record<string, any> }>();
const router = useRouter();

const isPublished = computed(() => !!props.form.is_published);
const submissionCount = computed<number>(() => props.form.submission_count ?? 0);

const publicUrl = computed(() =>
    props.form.route ? `${window.location.origin}/forms/p/${props.form.route}` : ""
);

/** "3 hours ago" style, because an exact timestamp isn't what you scan for. */
const lastActivity = computed(() => {
    const raw = props.form.last_submission_at;
    if (!raw) return null;

    const then = new Date(raw.replace(" ", "T"));
    const seconds = Math.floor((Date.now() - then.getTime()) / 1000);
    if (Number.isNaN(seconds)) return null;

    const units: [number, Intl.RelativeTimeFormatUnit][] = [
        [60, "second"],
        [3600, "minute"],
        [86400, "hour"],
        [604800, "day"],
        [2629800, "week"],
        [31557600, "month"],
    ];

    const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
    let previous = 1;
    for (const [limit, unit] of units) {
        if (seconds < limit) return rtf.format(-Math.floor(seconds / previous), unit);
        previous = limit;
    }
    return rtf.format(-Math.floor(seconds / 31557600), "year");
});

const createdOn = computed(() =>
    props.form.creation ? new Date(props.form.creation).toLocaleDateString() : ""
);

function openManage() {
    router.push({ name: "Manage Form", params: { id: props.form.name } });
}

function openBuilder() {
    router.push({ name: "Edit Form", params: { id: props.form.name } });
}

function openSubmissions() {
    router.push({ name: "Manage Form Submissions", params: { id: props.form.name } });
}

function openPublicForm() {
    if (publicUrl.value) window.open(publicUrl.value, "_blank", "noopener");
}

async function copyLink() {
    if (!publicUrl.value) return;
    try {
        await navigator.clipboard.writeText(publicUrl.value);
        toast.success("Form link copied");
    } catch {
        toast.error("Could not copy the link");
    }
}
</script>

<template>
    <div
        class="group flex flex-col justify-between gap-4 rounded-md border border-outline-gray-2 bg-surface-white p-4 transition-all duration-200 hover:border-outline-gray-3 hover:shadow-sm"
        data-form-card
    >
        <!-- Title + status -->
        <button type="button" class="flex flex-col gap-2 text-left" @click="openManage">
            <div class="flex items-start justify-between gap-2">
                <h3 class="text-base-semibold text-ink-gray-8 line-clamp-2">
                    {{ props.form.title || "Untitled Form" }}
                </h3>
                <Badge
                    class="shrink-0"
                    :label="isPublished ? 'Published' : 'Draft'"
                    :theme="isPublished ? 'green' : 'gray'"
                />
            </div>

            <p v-if="props.form.route" class="truncate font-mono text-xs text-ink-gray-4">
                /{{ props.form.route }}
            </p>
        </button>

        <!-- The numbers that say whether this form is actually working -->
        <button
            type="button"
            class="flex flex-col gap-1 rounded bg-surface-gray-1 px-3 py-2 text-left transition-colors hover:bg-surface-gray-2"
            @click="openSubmissions"
        >
            <div class="flex items-baseline gap-1.5">
                <Inbox class="size-3.5 shrink-0 self-center text-ink-gray-5" aria-hidden="true" />
                <span class="text-lg font-semibold tabular-nums text-ink-gray-8">
                    {{ submissionCount }}
                </span>
                <span class="text-xs text-ink-gray-5">
                    {{ submissionCount === 1 ? "submission" : "submissions" }}
                </span>
            </div>
            <p class="text-xs text-ink-gray-5">
                <template v-if="lastActivity">Last {{ lastActivity }}</template>
                <template v-else-if="isPublished">No submissions yet</template>
                <template v-else>Not collecting yet</template>
            </p>
        </button>

        <!-- Where the data lands, and the quick actions -->
        <div class="flex items-center justify-between gap-2">
            <Tooltip
                :text="
                    props.form.target_doctype
                        ? `Submissions are stored in ${props.form.target_doctype}`
                        : 'No target DocType set'
                "
                placement="bottom"
            >
                <span class="truncate text-xs text-ink-gray-5">
                    {{ props.form.target_doctype || "No target" }}
                    <span class="text-ink-gray-4"> · {{ createdOn }}</span>
                </span>
            </Tooltip>

            <div
                class="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100"
            >
                <Tooltip text="Edit form" placement="bottom">
                    <Button variant="ghost" size="sm" aria-label="Edit form" @click="openBuilder">
                        <Pencil class="size-4" aria-hidden="true" />
                    </Button>
                </Tooltip>
                <Tooltip v-if="props.form.route" text="Copy public link" placement="bottom">
                    <Button variant="ghost" size="sm" aria-label="Copy public link" @click="copyLink">
                        <Link2 class="size-4" aria-hidden="true" />
                    </Button>
                </Tooltip>
                <Tooltip
                    v-if="props.form.route"
                    :text="isPublished ? 'Open live form' : 'Preview (form is not published)'"
                    placement="bottom"
                >
                    <Button
                        variant="ghost"
                        size="sm"
                        aria-label="Open form in a new tab"
                        @click="openPublicForm"
                    >
                        <ExternalLink class="size-4" aria-hidden="true" />
                    </Button>
                </Tooltip>
            </div>
        </div>
    </div>
</template>
