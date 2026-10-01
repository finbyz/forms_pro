// @vitest-environment jsdom
/**
 * The builder keeps editing the form it saved.
 *
 * frappe-ui replaces the document with the server's copy after every save.
 * The properties panel edits the selected field object directly, so after the
 * first autosave it was editing a row no longer in the form: Select options
 * and conditions were silently not saved or published.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { reactive, nextTick, watch } from "vue";
import { createPinia, setActivePinia } from "pinia";

type Pending = { resolve: (doc: any) => void; reject: (err: any) => void };
const pendingSaves: Pending[] = [];
let lastResource: any = null;

vi.mock("vue-sonner", () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }));

vi.mock("frappe-ui", async (importOriginal) => {
  const actual: any = await importOriginal();
  // Mirrors frappe-ui's documentResource: a save swaps in the server's copy,
  // a failed one swaps in the pre-save copy.
  function createDocumentResource(options: any) {
    const out: any = reactive({
      doc: null,
      originalDoc: null,
      isDirty: false,
      loading: false,
      setValue: {
        loading: false,
        submit(values: any) {
          out.previousDoc = JSON.stringify(out.doc);
          Object.assign(out.doc, values);
          return new Promise((resolve, reject) => {
            pendingSaves.push({
              resolve: (data: any) => {
                out.doc = options.transform ? options.transform(data) : data;
                out.originalDoc = JSON.parse(JSON.stringify(out.doc));
                out.isDirty = false;
                resolve(data);
              },
              reject: (err: any) => {
                out.doc = JSON.parse(out.previousDoc);
                reject(err);
              },
            });
          });
        },
      },
      reload: vi.fn(),
    });
    // frappe-ui recomputes isDirty whenever the document changes.
    watch(
      () => out.doc,
      () => (out.isDirty = JSON.stringify(out.doc) !== JSON.stringify(out.originalDoc)),
      { deep: true, flush: "sync" }
    );
    lastResource = out;
    return out;
  }
  function createResource() {
    return { fetch: vi.fn(async () => undefined), submit: vi.fn(), data: null };
  }
  return { ...actual, createDocumentResource, createResource };
});

import { useEditForm } from "@/stores/editForm";

function serverCopy(doc: any, patch: (d: any) => void = () => {}) {
  const copy = JSON.parse(JSON.stringify(doc));
  copy.modified = "2026-10-01 10:00:05";
  copy.fields.forEach((f: any, i: number) => (f.name = f.name || `row${i + 1}`));
  patch(copy);
  return copy;
}

describe("saving in the form builder", () => {
  let store: ReturnType<typeof useEditForm>;

  beforeEach(async () => {
    vi.useFakeTimers();
    pendingSaves.length = 0;
    setActivePinia(createPinia());
    store = useEditForm();
    store.initialize("f1");
    lastResource.doc = {
      name: "f1",
      title: "Survey",
      modified: "2026-10-01 10:00:00",
      fields: [
        { fieldname: "color", fieldtype: "Select", label: "Color", options: "Red\nGreen" },
        { fieldname: "notes", fieldtype: "Data", label: "Notes" },
      ],
    };
    lastResource.originalDoc = JSON.parse(JSON.stringify(lastResource.doc));
    await nextTick();
  });

  afterEach(() => vi.useRealTimers());

  async function finishSave(patch?: (d: any) => void) {
    const save = pendingSaves.shift()!;
    save.resolve(serverCopy(lastResource.doc, patch));
    await vi.advanceTimersByTimeAsync(0);
  }

  it("keeps the selected field in the form after an autosave", async () => {
    store.selectField(store.fields[0]);
    store.selectedField!.options = "Red\nGreen\nBlue";
    lastResource.isDirty = true;

    const saving = store.save(undefined, true);
    await vi.advanceTimersByTimeAsync(0);
    await finishSave();
    await saving;

    expect(store.fields).toContain(store.selectedField);

    // Typed after the save: still lands in the form.
    store.selectedField!.options = "Red\nGreen\nBlue\nYellow";
    expect(store.fields[0].options).toBe("Red\nGreen\nBlue\nYellow");
  });

  it("keeps what was typed while the save was in flight, and saves it next", async () => {
    store.selectField(store.fields[0]);
    lastResource.isDirty = true;
    store.selectedField!.options = "Red\nGreen\nBlue";

    const saving = store.save(undefined, true);
    await vi.advanceTimersByTimeAsync(0);
    store.selectedField!.options = "Red\nGreen\nBlue\nYellow"; // during the save
    pendingSaves.shift()!.resolve(
      serverCopy({ ...lastResource.doc, fields: [{ ...lastResource.doc.fields[0], options: "Red\nGreen\nBlue" }, lastResource.doc.fields[1]] })
    );
    await saving;

    expect(store.fields[0].options).toBe("Red\nGreen\nBlue\nYellow");
    expect(store.isUnsaved).toBe(true);

    lastResource.isDirty = true;
    await vi.advanceTimersByTimeAsync(2000); // the follow-up autosave
    expect(pendingSaves.length).toBe(1);
  });

  it("re-attaches the panel when the field list is replaced", async () => {
    store.selectField(store.fields[1]);
    lastResource.doc.fields = JSON.parse(JSON.stringify(lastResource.doc.fields));
    expect(store.selectedField).toBe(store.fields[1]);
  });

  it("keeps the edits when a save fails", async () => {
    store.selectField(store.fields[0]);
    store.selectedField!.options = "Red\nGreen\nBlue";
    lastResource.isDirty = true;

    const saving = store.save(undefined, true);
    await vi.advanceTimersByTimeAsync(0);
    pendingSaves.shift()!.reject(new Error("network"));
    await expect(saving).rejects.toThrow("network");

    expect(store.fields).toContain(store.selectedField);
    expect(store.fields[0].options).toBe("Red\nGreen\nBlue");
    // A failure is reported, not retried in a loop.
    await vi.advanceTimersByTimeAsync(5000);
    expect(pendingSaves.length).toBe(0);
  });
});
