import { computed, ref, watch } from "vue";
import { createResource } from "frappe-ui";

export interface SubmissionFilter {
    /** Which side of the record this filter reads: a column, or one of the form's questions. */
    source: "column" | "answer";
    field: string;
    operator: string;
    value: any;
}

export interface FilterFieldOption {
    field: string;
    label: string;
    fieldtype?: string;
    options?: string | null;
}

/** Operators that take no value, so the UI hides the value box for them. */
export const VALUELESS_OPERATORS = ["is set", "is not set"];
/** Operators whose value is a list rather than a scalar. */
export const LIST_OPERATORS = ["in", "not in", "between"];

/**
 * One page of a form's submissions, resolved on the server.
 *
 * Every filter, the sort and the count are sent to the database rather than
 * applied to whatever happened to be loaded. Filtering a loaded page is the
 * trap this replaces: it reads like a search of the whole form but answers
 * from the current page, so an operator concludes a submission does not exist.
 */
export function useSubmissionQuery(formId: () => string, options: { pageLength?: number } = {}) {
    const filters = ref<SubmissionFilter[]>([]);
    const search = ref("");
    const sortField = ref("submitted_at");
    const sortDirection = ref<"asc" | "desc">("desc");
    const pageLength = ref(options.pageLength ?? 20);
    const start = ref(0);
    const rows = ref<any[]>([]);
    const total = ref(0);
    const hasMore = ref(false);
    const loading = ref(false);
    const error = ref("");

    const pageLengths = ref<number[]>([20, 100, 500]);
    const columnFields = ref<FilterFieldOption[]>([]);
    const answerFields = ref<FilterFieldOption[]>([]);
    const operators = ref<string[]>([]);

    const listResource = createResource({ url: "forms_pro.api.submission.list_submissions" });
    const fieldsResource = createResource({ url: "forms_pro.api.submission.get_submission_filter_fields" });

    /** Only complete filters are sent; a half-built row must not empty the list. */
    function usable(entry: SubmissionFilter) {
        if (!entry.field || !entry.operator) return false;
        if (VALUELESS_OPERATORS.includes(entry.operator)) return true;
        if (Array.isArray(entry.value)) return entry.value.length > 0;
        return entry.value !== "" && entry.value !== null && entry.value !== undefined;
    }

    function serialise(source: "column" | "answer") {
        return filters.value
            .filter((entry) => entry.source === source && usable(entry))
            .map((entry) => [entry.field, entry.operator, entry.value ?? null]);
    }

    async function fetchPage() {
        const form = formId();
        if (!form) return;
        loading.value = true;
        error.value = "";
        try {
            const page = await listResource.submit({
                form_id: form,
                filters: JSON.stringify(serialise("column")),
                answer_filters: JSON.stringify(serialise("answer")),
                search: search.value.trim(),
                order_by: `${sortField.value} ${sortDirection.value}`,
                limit_start: start.value,
                limit_page_length: pageLength.value,
            });
            rows.value = page?.rows ?? [];
            total.value = page?.total ?? 0;
            hasMore.value = Boolean(page?.has_more);
            if (Array.isArray(page?.page_lengths)) pageLengths.value = page.page_lengths;
        } catch (err: any) {
            // A rejected filter must not leave stale rows looking like a result.
            rows.value = [];
            total.value = 0;
            hasMore.value = false;
            error.value = err?.message || "Could not load submissions";
        } finally {
            loading.value = false;
        }
    }

    async function loadFilterFields() {
        const form = formId();
        if (!form) return;
        try {
            const meta = await fieldsResource.submit({ form_id: form });
            columnFields.value = meta?.columns ?? [];
            answerFields.value = meta?.answers ?? [];
            operators.value = meta?.operators ?? [];
            if (Array.isArray(meta?.page_lengths)) pageLengths.value = meta.page_lengths;
        } catch {
            /* the list still works without the filter catalogue */
        }
    }

    /** Any change to what is being asked returns to the first page. */
    function reload() {
        start.value = 0;
        return fetchPage();
    }

    function addFilter(source: "column" | "answer" = "column") {
        const pool = source === "column" ? columnFields.value : answerFields.value;
        filters.value.push({ source, field: pool[0]?.field ?? "", operator: "=", value: "" });
    }

    function removeFilter(index: number) {
        filters.value.splice(index, 1);
        reload();
    }

    function clearFilters() {
        filters.value = [];
        search.value = "";
        reload();
    }

    function setSort(field: string) {
        if (sortField.value === field) {
            sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
        } else {
            sortField.value = field;
            sortDirection.value = "desc";
        }
        reload();
    }

    const page = computed(() => Math.floor(start.value / pageLength.value) + 1);
    const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageLength.value)));
    const rangeFrom = computed(() => (total.value === 0 ? 0 : start.value + 1));
    const rangeTo = computed(() => start.value + rows.value.length);
    const activeFilterCount = computed(() => filters.value.filter(usable).length);

    function nextPage() {
        if (!hasMore.value) return;
        start.value += pageLength.value;
        fetchPage();
    }

    function previousPage() {
        if (start.value === 0) return;
        start.value = Math.max(0, start.value - pageLength.value);
        fetchPage();
    }

    function goToPage(target: number) {
        const bounded = Math.min(Math.max(1, target), pageCount.value);
        start.value = (bounded - 1) * pageLength.value;
        fetchPage();
    }

    /** Changing the page size keeps the operator near the rows they were reading. */
    watch(pageLength, (length) => {
        start.value = Math.floor(start.value / length) * length;
        fetchPage();
    });

    return {
        filters, search, sortField, sortDirection, pageLength, start,
        rows, total, hasMore, loading, error,
        pageLengths, columnFields, answerFields, operators,
        page, pageCount, rangeFrom, rangeTo, activeFilterCount,
        fetchPage, loadFilterFields, reload, addFilter, removeFilter, clearFilters,
        setSort, nextPage, previousPage, goToPage,
    };
}
