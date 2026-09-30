import { defineStore } from "pinia";
import { canonicalHtml } from "@/utils/html_equivalence";
import { sameDoc } from "@/utils/doc_equivalence";
import { ref, computed, watch, onUnmounted, nextTick } from "vue";
import { createDocumentResource, createResource } from "frappe-ui";
import {
  mapDoctypeFieldForForm,
  scrubFieldname,
  compact,
  isDisplayOnly,
} from "@/utils/form_fields";
import { placeBesideAbove } from "@/utils/form_layout";
import {
  groupFieldsIntoSteps,
  insertFieldAtStepEnd,
  appendStep,
  removeStepKeepFields as removeStepKeepFieldsUtil,
  removeStepWithFields as removeStepWithFieldsUtil,
  renameStep as renameStepUtil,
  type FormStep,
} from "@/utils/form_steps";
import { FormField, Fieldtype } from "@/types/formfield";
import { Form } from "@/types/form";
import { toast } from "vue-sonner";
import { dialog } from "@/utils/dialog";
import { useHistoryStore } from "@/stores/history";

export const useEditForm = defineStore("editForm", () => {
  const formResource = ref<any>(null);
  const currentFormId = ref<string | null>(null);
  const selectedField = ref<FormField | null>(null);
  const activeSectionIndex = ref<number | 'success'>(0);
  // "Unsaved" means the content differs from the saved copy, not merely its
  // bytes -- see utils/doc_equivalence.ts for the loop the raw flag caused.
  const isUnsaved = computed(
    () =>
      Boolean(formResource.value?.isDirty) &&
      !sameDoc(formResource.value?.doc, formResource.value?.originalDoc)
  );
  const isLoading = computed(() => formResource.value?.loading || false);
  const isSaving = computed(
    () => formResource.value?.setValue?.loading || false
  );
  const isPublished = computed(
    () => formResource.value?.doc?.is_published || false
  );

  const doctypeFields = ref<any>([]);

  // True while a field is being dragged from anywhere — the canvas, the
  // Add Fields palette or the DocType list. The drop zones are invisible
  // unless this is set, so every drag source has to flip it.
  const isDraggingField = ref(false);
  /**
   * The field currently being dragged, if it is one already on the canvas.
   *
   * The drop geometry measures the layout around the pointer and has to leave
   * this field out: a field cannot be a landmark for deciding where it should
   * go, and including it makes the indicator stick to where the field already
   * is.
   */
  const draggingFieldname = ref<string | null>(null);
  function setDragging(value: boolean, fieldname: string | null = null) {
    isDraggingField.value = value;
    draggingFieldname.value = value ? fieldname : null;
  }

  const isError = computed(() => formResource.value?.error || false);
  const formData = computed(() => formResource.value?.doc || null);
  const fields = computed(() => {
    return formResource.value?.doc?.fields || [];
  });

  const sections = computed<FormStep[]>(() =>
    groupFieldsIntoSteps(fields.value, {
      labelFallback: (n) => `Step ${n}`,
      alwaysIncludeTrailing: true,
    })
  );

  const isMultiSection = computed(() => sections.value.length > 1);

  const activeSectionFields = computed(() => {
    if (activeSectionIndex.value === 'success') return [];
    return sections.value[activeSectionIndex.value as number]?.fields ?? [];
  });
  const originalFormData = computed(
    () => formResource.value?.originalDoc || null
  );

  // History (undo/redo)
  const history = useHistoryStore();
  let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
  const AUTOSAVE_DEBOUNCE_MS = 1500;
  const MAX_HISTORY = 50;
  let skipSnapshot = false;

  function snapshot() {
    if (skipSnapshot || !formResource.value?.doc?.fields) return;
    history.saveState({
      fields: JSON.parse(JSON.stringify(formResource.value.doc.fields)),
      title: formResource.value.doc.title,
    });
    if (history.past.length > MAX_HISTORY) {
      history.past.shift();
    }
  }

  function undo() {
    if (history.past.length === 0 || !formResource.value?.doc) return;
    skipSnapshot = true;
    try {
      const prev = history.undo({
        fields: JSON.parse(JSON.stringify(formResource.value.doc.fields)),
        title: formResource.value.doc.title,
      });
      if (prev) {
        formResource.value.doc.fields = prev.fields;
        formResource.value.doc.title = prev.title;
        formResource.value.isDirty = true;
        triggerAutosave();
      }
    } finally {
      skipSnapshot = false;
    }
  }

  function redo() {
    if (history.future.length === 0 || !formResource.value?.doc) return;
    skipSnapshot = true;
    try {
      const next = history.redo({
        fields: JSON.parse(JSON.stringify(formResource.value.doc.fields)),
        title: formResource.value.doc.title,
      });
      if (next) {
        formResource.value.doc.fields = next.fields;
        formResource.value.doc.title = next.title;
        formResource.value.isDirty = true;
        triggerAutosave();
      }
    } finally {
      skipSnapshot = false;
    }
  }

  const canUndo = computed(() => history.past.length > 0);
  const canRedo = computed(() => history.future.length > 0);

  // Autosave
  function triggerAutosave() {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(async () => {
      if (!formResource.value) return;
      try {
        // Autosave is background work — only failures are worth interrupting for.
        await save(undefined, true);
      } catch {
        // silent fail — user can still manually save
      }
    }, AUTOSAVE_DEBOUNCE_MS);
  }

  function cancelAutosave() {
    if (autosaveTimer) {
      clearTimeout(autosaveTimer);
      autosaveTimer = null;
    }
  }

  // Watch fields for autosave + history snapshots
  watch(
    () => formResource.value?.doc?.fields,
    (_new, _old) => {
      if (!skipSnapshot && formResource.value?.doc?.fields) {
        snapshot();
        triggerAutosave();
      }
    },
    { deep: true }
  );

  /**
   * The form's own title and description are edited straight on the canvas,
   * but the watcher above only looks at `fields`. So typing in the description
   * -- a heading and then a paragraph, say -- changed the document without
   * anything noticing: no autosave, no "Saving...", and no "Publish changes"
   * until some unrelated field edit happened to carry it along.
   */
  //
  // Watched as one string, not as an array: a getter returning a new array is
  // "changed" every time it runs, and every save replaces the document, so the
  // save's own response looked like an edit and started the next save. And
  // the description is compared in canonical form, because the server rewrites
  // inline styles on the way in -- see utils/html_equivalence.ts.
  watch(
    () =>
      `${formResource.value?.doc?.title ?? ""}\u0000${canonicalHtml(
        formResource.value?.doc?.description
      )}`,
    () => {
      if (skipSnapshot || !formResource.value?.doc) return;
      formResource.value.isDirty = true;
      snapshot();
      triggerAutosave();
    }
  );

  // Dirty-state: warn before leaving
  function setupDirtyGuard() {
    const handler = (e: BeforeUnloadEvent) => {
      if (isUnsaved.value) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }

  let removeDirtyGuard: (() => void) | null = null;
  function enableDirtyGuard() {
    if (!removeDirtyGuard) removeDirtyGuard = setupDirtyGuard();
  }
  function disableDirtyGuard() {
    if (removeDirtyGuard) {
      removeDirtyGuard();
      removeDirtyGuard = null;
    }
  }

  onUnmounted(() => {
    cancelAutosave();
    disableDirtyGuard();
  });

  /** Which DocType the form writes to, and whether the form created it. */
  const targetInfo = ref<{
    doctype: string | null;
    module: string | null;
    owned: boolean;
    naming: { summary: string; series: string[]; configured_in: string | null } | null;
  } | null>(null);

  async function loadTargetInfo(doctype?: string) {
    if (!currentFormId.value) return;
    const res = createResource({
      url: "forms_pro.api.form.get_target_doctype_info",
      params: {
        form_id: currentFormId.value,
        ...(doctype ? { doctype } : {}),
      },
    });
    try {
      await res.fetch();
      targetInfo.value = res.data ?? null;
    } catch {
      targetInfo.value = null;
    }
  }

  async function getDoctypeFields() {
    await loadTargetInfo();
    if (formResource.value?.doc?.target_doctype) {
      const _fields = createResource({
        url: "forms_pro.api.form.get_doctype_fields",
        method: "GET",
        makeParams() {
          return {
            doctype: formResource.value?.doc?.target_doctype,
          };
        },
        transform: (data: any) => {
          return data.map((field: any) => {
            return {
              ...field,
              fieldtype: mapDoctypeFieldForForm(field.fieldtype, field.options),
            };
          });
        },
      });

      await _fields.fetch();
      doctypeFields.value = _fields.data;
    }
  }

  function initialize(formId: string) {
    // Coming back to a form already opened in this session. The store keeps
    // the copy it loaded last time, and this used to return without looking at
    // the server again -- so unpublishing from the form's overview page and
    // then opening the builder still showed "Published", and the other way
    // round. Anything still waiting to autosave is written first, so the
    // reload cannot throw an edit away.
    if (formId === currentFormId.value && formResource.value) {
      void refreshFromServer();
      return;
    }
    if (formId !== currentFormId.value) {
      currentFormId.value = formId;
      // Suppressed until the document has hydrated; see onSuccess below.
      skipSnapshot = true;
      formResource.value = createDocumentResource({
        doctype: "Form",
        name: formId,
        transform: (doc: Form) => {
          return {
            ...doc,
            title: doc.title === "Untitled Form" ? "" : doc.title,
          };
        },
        onSuccess: () => {
          getDoctypeFields();
          enableDirtyGuard();
          refreshPublishState();
          // The deep watcher on doc.fields fires once as the document
          // hydrates, which otherwise schedules an autosave the moment the
          // builder opens -- the user sees "Saving..." without having touched
          // anything. Re-arm only after that first firing has passed.
          nextTick(() => {
            skipSnapshot = false;
            cancelAutosave();
            snapshot(); // baseline for undo
          });
        },
      });
    }
  }

  function reload() {
    if (formResource.value) {
      // The reloaded document replaces the old one wholesale, which the field
      // and title watchers would otherwise read as an edit and autosave. The
      // resource's onSuccess re-arms them once it has hydrated.
      skipSnapshot = true;
      formResource.value.reload();
    }
  }

  async function refreshFromServer() {
    cancelAutosave();
    if (isUnsaved.value) {
      try {
        await save(undefined, true);
      } catch {
        // save() has already reported it; reloading now would drop the edit.
        return;
      }
    }
    reload();
  }

  function reset() {
    currentFormId.value = null;
    formResource.value = null;
  }

  /**
   * Form Field has reqd=1 on both label and fieldname, and autosave fires as
   * soon as a field is added — so a field created with an empty label throws a
   * mandatory error before the user can type anything. Give it a unique
   * placeholder label up front.
   */
  function uniqueDefaultLabel(fieldtype: Fieldtype): string {
    const fs: FormField[] = formResource.value?.doc?.fields ?? [];
    const taken = new Set(fs.map((f: FormField) => (f.label ?? "").trim()));
    if (!taken.has(fieldtype)) return fieldtype;
    let n = 2;
    while (taken.has(`${fieldtype} ${n}`)) n++;
    return `${fieldtype} ${n}`;
  }

  function findDuplicateFieldnames(): { label: string; fieldname: string }[] {
    const allFields = formResource.value?.doc?.fields || [];
    const seen = new Map<string, FormField>();
    const duplicates: { label: string; fieldname: string }[] = [];

    for (const field of allFields) {
      const name = field.fieldname?.trim()
        ? field.fieldname
        : scrubFieldname(field.label);

      if (seen.has(name)) {
        const existing = seen.get(name)!;
        if (!duplicates.some((d) => d.fieldname === name)) {
          duplicates.push({ label: existing.label, fieldname: name });
        }
        duplicates.push({ label: field.label, fieldname: name });
      }
      seen.set(name, field);
    }

    return duplicates;
  }

  /**
   * Autosave, the Save button and publish all write the same document. When two
   * of them overlap the second sends a stale `modified` and Frappe rejects it
   * with TimestampMismatchError, so saves are serialized and retried once
   * against a refreshed timestamp.
   */
  let inFlightSave: Promise<unknown> | null = null;

  async function refreshModifiedTimestamp(): Promise<void> {
    const id = currentFormId.value;
    if (!id || !formResource.value?.doc) return;
    const latest = createResource({
      url: "frappe.client.get_value",
      params: { doctype: "Form", filters: { name: id }, fieldname: "modified" },
    });
    await latest.fetch();
    if (latest.data?.modified) {
      formResource.value.doc.modified = latest.data.modified;
    }
  }

  function isTimestampMismatch(error: any): boolean {
    return (
      error?.exc_type === "TimestampMismatchError" ||
      /TimestampMismatchError|Document has been modified/i.test(
        error?.message ?? ""
      )
    );
  }

  async function persist(successMessage?: string, silent = false): Promise<unknown> {
    const submit = () => formResource.value.setValue.submit(formResource.value.doc);

    try {
      const result = await submit();
      if (!silent) toast.success(successMessage ?? "Form Updated Successfully");
      return result;
    } catch (error: any) {
      if (isTimestampMismatch(error)) {
        // Someone (usually our own autosave) got there first. Our in-memory
        // document is the newer one, so re-stamp it and write again.
        await refreshModifiedTimestamp();
        const result = await submit();
        if (!silent) toast.success(successMessage ?? "Form Updated Successfully");
        return result;
      }
      toast.error("Failed to Update Form", { description: error?.message });
      throw error;
    }
  }

  async function save(successMessage?: string, silent = false) {
    if (inFlightSave) {
      // Wait for the running save so we build on its timestamp, not a stale one.
      try {
        await inFlightSave;
      } catch {
        // the originating call reports its own failure
      }
    }

    if (!isUnsaved.value) {
      return;
    }

    if (!formResource.value) {
      toast.error("No form resource available");
      return Promise.reject(new Error("No form resource available"));
    }

    // Ensure title is never empty
    if (!formResource.value.doc.title || !formResource.value.doc.title.trim()) {
      formResource.value.doc.title = "Untitled Form";
    }

    const duplicates = findDuplicateFieldnames();
    if (duplicates.length > 0) {
      const fieldList = duplicates
        .map((d) => `<b>${d.label} (${d.fieldname})</b>`)
        .join(", ");
      await dialog.alert({
        title: "Duplicate Fieldnames",
        message: `These fields will have duplicate fieldnames: ${fieldList}. Please change one of the labels or set a unique fieldname.`,
        html: true,
      });
      return Promise.reject(new Error("Duplicate fieldnames"));
    }

    const usedFieldnames = new Set<string>();
    formResource.value.doc.fields.forEach((field: FormField, index: number) => {
      field.idx = index + 1;
      if (!field.label || !field.label.trim()) {
        field.label = uniqueDefaultLabel(field.fieldtype);
      }
      if (!field.fieldname || field.fieldname.trim() === "") {
        // scrubFieldname("") is "", which trips the doctype's reqd fieldname.
        const base = scrubFieldname(field.label) || "field";
        let candidate = base;
        let n = 2;
        while (usedFieldnames.has(candidate)) candidate = `${base}_${n++}`;
        field.fieldname = candidate;
      }
      usedFieldnames.add(field.fieldname);
    });

    inFlightSave = persist(successMessage, silent);
    try {
      return await inFlightSave;
    } finally {
      inFlightSave = null;
      // Saving the draft may create a gap with the published snapshot.
      refreshPublishState();
    }
  }

  function saveAndPublish() {
    if (formResource.value) {
      formResource.value.doc.is_published = 1;
      return save();
    }
  }

  // Publishing state: the draft the builder edits vs the snapshot visitors get.
  const publishState = ref<{
    is_published: boolean;
    active_version: string | null;
    version_number: number | null;
    has_unpublished_changes: boolean;
    never_published: boolean;
  } | null>(null);

  const hasUnpublishedChanges = computed(
    () => publishState.value?.has_unpublished_changes ?? false
  );
  const neverPublished = computed(
    () => publishState.value?.never_published ?? true
  );

  /**
   * Only the newest answer about publish state may be shown.
   *
   * Saving asks the server for the publish state without waiting, and the
   * publish button saves first when there is anything unsaved -- so the
   * question "are there unpublished changes?" went out *before* the publish,
   * and its answer ("yes") could arrive *after* the publish had answered
   * "no". The stale answer won, "Publish changes" came straight back, and a
   * second click published the same thing again. Ticking "Allow Partial
   * Submissions" and pressing Publish straight away hit it every time.
   */
  let publishStateSeq = 0;

  async function refreshPublishState() {
    if (!currentFormId.value) return;
    const seq = ++publishStateSeq;
    const res = createResource({
      url: "forms_pro.api.v1.builder.publishing.get_publish_state",
      params: { form_id: currentFormId.value },
    });
    await res.fetch();
    if (seq !== publishStateSeq) return;
    publishState.value = res.data ?? null;
  }

  /** Compile the draft into a new version and serve it to visitors. */
  async function publish() {
    if (!currentFormId.value) return;
    // Publish what is on screen, not what was last autosaved -- and do not
    // let a pending autosave run a second save in the middle of it.
    cancelAutosave();
    if (isUnsaved.value) await save(undefined, true);

    const res = createResource({
      url: "forms_pro.api.v1.builder.publishing.publish_form",
      method: "POST",
      makeParams: () => ({ form_id: currentFormId.value }),
    });
    try {
      await res.fetch();
      publishStateSeq++; // anything asked before the publish is now stale
      publishState.value = res.data ?? null;
      if (formResource.value?.doc) formResource.value.doc.is_published = 1;
      toast.success(
        res.data?.version_number > 1
          ? `Published version ${res.data.version_number} — changes are now live`
          : "Form published successfully"
      );
    } catch (error: any) {
      toast.error("Failed to publish form", { description: error?.message });
      throw error;
    }
  }

  async function unpublish() {
    if (!currentFormId.value) return;
    const res = createResource({
      url: "forms_pro.api.v1.builder.publishing.unpublish_form",
      method: "POST",
      makeParams: () => ({ form_id: currentFormId.value }),
    });
    try {
      await res.fetch();
      publishStateSeq++;
      publishState.value = res.data ?? null;
      if (formResource.value?.doc) formResource.value.doc.is_published = 0;
      toast.info("Form unpublished — it is no longer accepting responses");
    } catch (error: any) {
      toast.error("Failed to unpublish form", { description: error?.message });
      throw error;
    }
  }

  async function togglePublish() {
    if (isPublished.value) await unpublish();
    else await publish();
  }

  function updateFormData(data: Partial<Form>) {
    if (formResource.value?.doc) {
      Object.assign(formResource.value.doc, data);
    }
  }

  function addField(fieldtype: Fieldtype) {
    if (!formResource.value?.doc) return;
    const fs: FormField[] = formResource.value.doc.fields;

    const newField: FormField = {
      idx: fs.length + 1,
      fieldtype,
      label: uniqueDefaultLabel(fieldtype),
      fieldname: "",
      options: "",
      default: "",
      description: "",
      // Fields added from the palette are form-only until the user binds
      // them to a target field; headings/page breaks never bind at all.
      source_type: isDisplayOnly(fieldtype) ? "Presentation" : "Form Field",
      row_index: 0,
      column_index: 0,
      cell_index: 0,
    };

    insertFieldAtStepEnd(
      fs,
      newField,
      activeSectionIndex.value === 'success' ? 0 : activeSectionIndex.value as number,
      isMultiSection.value
    );
  }

  /**
   * Turn a DocType field (as returned by get_doctype_fields) into a form field
   * bound to it. Does not place the field — callers decide where it lands.
   */
  function buildFieldFromDoctype(field: any, idx: number): FormField {
    // The sidebar already maps fieldtype, but re-resolve here so a field added
    // by any path inherits Email/Phone semantics from the DocType.
    // Never fall back to the raw Frappe fieldtype -- it is not one of ours and
    // the renderer cannot draw it. Anything unmapped becomes a text box.
    const resolved =
      (mapDoctypeFieldForForm(field.fieldtype, field.options) as Fieldtype) ??
      Fieldtype.DATA;

    /**
     * A column the visitor cannot fill in.
     *
     * Three separate signals mean the same thing: the column is flagged
     * read only, its Frappe type *is* "Read Only", or its value is fetched
     * from another document (Supplier's Mobile and Email are pulled from the
     * primary contact). In every case a submitted value would be ignored or
     * overwritten, so the field is shown but not editable.
     */
    const isReadOnly =
      !!field.read_only || field.fieldtype === "Read Only" || !!field.fetch_from;

    // "Email"/"Phone" are markers, not a Select option list.
    const isSemanticMarker =
      resolved === Fieldtype.EMAIL || resolved === Fieldtype.PHONE;

    return {
      idx,
      fieldtype: resolved,
      label: field.label,
      fieldname: field.fieldname,
      options: isSemanticMarker ? "" : field.options,
      default: field.default,
      description: field.description,
      // A field imported from the target DocType inherits its mandatoriness.
      // A read-only column cannot also be required of the visitor.
      reqd: isReadOnly ? false : !!field.reqd,
      read_only: isReadOnly,
      mapping_type: "Direct",
      target_field: field.fieldname,
      source_type: "Target Field",
      row_index: 0,
      column_index: 0,
      cell_index: 0,
    };
  }

  function addFieldFromDoctype(field: any) {
    if (!formResource.value?.doc) return;
    const fs: FormField[] = formResource.value.doc.fields;

    insertFieldAtStepEnd(
      fs,
      buildFieldFromDoctype(field, fs.length + 1),
      activeSectionIndex.value === 'success' ? 0 : activeSectionIndex.value as number,
      isMultiSection.value
    );
  }

  /**
   * Drag-and-drop entry point for the Add Fields palette: creates a blank field
   * of the given type and returns it for positioning.
   */
  function materializeNewField(fieldtype: Fieldtype): FormField | null {
    if (!formResource.value?.doc) return null;
    const fs: FormField[] = formResource.value.doc.fields;
    const newField: FormField = {
      idx: fs.length + 1,
      fieldtype,
      label: uniqueDefaultLabel(fieldtype),
      fieldname: "",
      options: "",
      default: "",
      description: "",
      source_type: isDisplayOnly(fieldtype) ? "Presentation" : "Form Field",
      row_index: 0,
      column_index: 0,
      cell_index: 0,
    };
    fs.push(newField);
    return newField;
  }

  /**
   * Drag-and-drop entry point. A drag from the DocType panel carries only a
   * fieldname; the field it names is not a FormField and is not yet in
   * doc.fields, so moveField/insertCell/insertNewRow would reject it. Push a
   * real field in first and hand that back for positioning.
   */
  function materializeDoctypeField(source: any): FormField | null {
    if (!formResource.value?.doc) return null;
    const fs: FormField[] = formResource.value.doc.fields;
    const newField = buildFieldFromDoctype(source, fs.length + 1);
    fs.push(newField);
    return newField;
  }

  function isFormField(field: any): boolean {
    const fs: FormField[] = formResource.value?.doc?.fields ?? [];
    return fs.includes(field);
  }

  /**
   * Point the form at a DocType, refresh the palette, and seed its mandatory
   * fields. Shared by the Settings tab and the builder sidebar.
   */
  async function setTargetDoctype(
    doctype: string
  ): Promise<{ changed: boolean; seeded: number; hadMappings: boolean }> {
    const idle = { changed: false, seeded: 0, hadMappings: false };
    if (!formResource.value?.doc || !doctype) return idle;
    if (doctype === formResource.value.doc.target_doctype) return idle;

    const hadMappings = (formResource.value.doc.fields ?? []).some(
      (f: FormField) => f.source_type === "Target Field"
    );

    formResource.value.doc.target_doctype = doctype;
    formResource.value.isDirty = true;
    triggerAutosave();

    await getDoctypeFields();

    // Changing DocType invalidates existing mappings, so don't pile new
    // fields on top — let the user review what's there first.
    const seeded = hadMappings ? 0 : seedMandatoryFields();
    return { changed: true, seeded, hadMappings };
  }

  /**
   * Add every mandatory field of the target DocType that the form does not
   * already map. Returns how many were added.
   */
  function seedMandatoryFields(): number {
    if (!formResource.value?.doc) return 0;
    const fs: FormField[] = formResource.value.doc.fields;
    const alreadyMapped = new Set(
      fs.map((f: FormField) => f.target_field).filter(Boolean)
    );

    const missing = (doctypeFields.value ?? []).filter(
      (f: any) => f.reqd && !alreadyMapped.has(f.fieldname)
    );

    for (const field of missing) {
      addFieldFromDoctype(field);
    }
    return missing.length;
  }

  function moveField(field: FormField, targetRow: number, targetCol: number) {
    const fs: FormField[] = formResource.value?.doc?.fields ?? [];
    if (!fs.includes(field)) return;

    // Shift existing columns in target row to open a slot (whole columns shift,
    // multi-cell columns stay grouped because all their cells share column_index)
    for (const f of fs) {
      if (
        f !== field &&
        (f.row_index ?? 0) === targetRow &&
        (f.column_index ?? 0) >= targetCol
      ) {
        f.column_index = (f.column_index ?? 0) + 1;
      }
    }

    field.row_index = targetRow;
    field.column_index = targetCol;
    field.cell_index = 0;

    compact(fs);
  }

  function insertCell(
    field: FormField,
    targetRow: number,
    targetCol: number,
    atCell: number
  ) {
    const fs: FormField[] = formResource.value?.doc?.fields ?? [];
    if (!fs.includes(field)) return;

    // Shift cells at or below atCell within (targetRow, targetCol) down by 1
    for (const f of fs) {
      if (
        f !== field &&
        (f.row_index ?? 0) === targetRow &&
        (f.column_index ?? 0) === targetCol &&
        (f.cell_index ?? 0) >= atCell
      ) {
        f.cell_index = (f.cell_index ?? 0) + 1;
      }
    }

    field.row_index = targetRow;
    field.column_index = targetCol;
    field.cell_index = atCell;

    compact(fs);
  }

  /**
   * Put a field beside the one above it, turning that row into two columns.
   *
   * The only way a column gets made. Dragging used to create one whenever the
   * pointer strayed near the side of a field, which meant a plain drag up or
   * down kept splitting rows nobody meant to split. A drag now only moves
   * fields between the columns that already exist; "Move to own row" undoes
   * this one.
   */
  function moveBesideAbove(field: FormField) {
    const fs: FormField[] = formResource.value?.doc?.fields ?? [];
    placeBesideAbove(fs, field);
  }

  function insertNewRow(field: FormField, atRow: number) {
    const fs: FormField[] = formResource.value?.doc?.fields ?? [];
    if (!fs.includes(field)) return;

    // Push all rows at or below atRow down by 1
    for (const f of fs) {
      if (f !== field && (f.row_index ?? 0) >= atRow) {
        f.row_index = (f.row_index ?? 0) + 1;
      }
    }

    field.row_index = atRow;
    field.column_index = 0;
    field.cell_index = 0;

    compact(fs);
  }

  function removeField(field: FormField) {
    if (formResource.value?.doc?.fields) {
      formResource.value.doc.fields = formResource.value.doc.fields.filter(
        (f: FormField) => f !== field
      );
      compact(formResource.value.doc.fields);
    }
  }

  function clampActiveStep() {
    if (activeSectionIndex.value === 'success') return;
    if ((activeSectionIndex.value as number) >= sections.value.length) {
      activeSectionIndex.value = sections.value.length - 1;
    }
  }

  function addStep() {
    const fs: FormField[] = formResource.value?.doc?.fields;
    if (!fs) return;

    const count = sections.value.length;
    appendStep(fs, count);
    activeSectionIndex.value = count;
  }

  /**
   * Move a field into another step.
   *
   * Steps are delimited by Page Break rows in one flat field list, so a field
   * "belongs" to a step purely by where it sits between those breaks. There was
   * no way to change that from the builder at all -- the step tabs are not drop
   * targets and no action offered it -- so a field added to the wrong step was
   * stuck there.
   */
  function moveFieldToStep(field: FormField, targetStepIndex: number) {
    const fs: FormField[] = formResource.value?.doc?.fields;
    if (!fs) return;

    const from = fs.indexOf(field);
    if (from === -1) return;
    if (targetStepIndex < 0 || targetStepIndex >= sections.value.length) return;

    fs.splice(from, 1);
    insertFieldAtStepEnd(fs, field, targetStepIndex, sections.value.length > 1);
    compact(fs);

    activeSectionIndex.value = targetStepIndex;
    selectedField.value = field;
    snapshot();
    triggerAutosave();
  }

  function removeStepKeepFields(index: number) {
    const fs: FormField[] = formResource.value?.doc?.fields;
    if (!fs) return;
    removeStepKeepFieldsUtil(fs, sections.value, index);
    clampActiveStep();
  }

  function removeStepWithFields(index: number) {
    const fs: FormField[] = formResource.value?.doc?.fields;
    if (!fs) return;
    removeStepWithFieldsUtil(fs, sections.value, index);
    clampActiveStep();
  }

  function renameStep(index: number, newLabel: string) {
    const fs: FormField[] = formResource.value?.doc?.fields;
    if (!fs) return;
    renameStepUtil(fs, index, newLabel);
  }

  function selectField(field: FormField | null) {
    selectedField.value = field;
  }

  function updateField(originalField: FormField, updatedField: FormField) {
    if (formResource.value?.doc?.fields) {
      const fieldIndex = formResource.value.doc.fields.findIndex(
        (f: FormField) => f === originalField
      );
      if (fieldIndex !== -1) {
        formResource.value.doc.fields[fieldIndex] = updatedField;
      }
    }
  }

  return {
    // State
    currentFormId,
    formResource,
    isUnsaved,

    // Computed
    originalFormData,
    isLoading,
    isSaving,
    isError,
    formData,
    fields,
    selectedField,
    isPublished,
    doctypeFields,
    targetInfo,
    publishState,
    hasUnpublishedChanges,
    neverPublished,
    isDraggingField,
    draggingFieldname,
    setDragging,
    sections,
    isMultiSection,
    activeSectionFields,
    activeSectionIndex,
    canUndo,
    canRedo,

    // Actions
    initialize,
    reload,
    reset,
    save,
    saveAndPublish,
    togglePublish,
    publish,
    unpublish,
    refreshPublishState,
    updateFormData,
    addField,
    addFieldFromDoctype,
    addStep,
    moveFieldToStep,
    removeStepKeepFields,
    removeStepWithFields,
    renameStep,
    selectField,
    updateField,
    removeField,
    moveField,
    insertCell,
    insertNewRow,
    moveBesideAbove,
    undo,
    redo,
    snapshot,
    triggerAutosave,
    cancelAutosave,
    enableDirtyGuard,
    disableDirtyGuard,
    getDoctypeFields,
    materializeDoctypeField,
    materializeNewField,
    isFormField,
    seedMandatoryFields,
    setTargetDoctype,
    loadTargetInfo,
  };
});
