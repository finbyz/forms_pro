import { describe, it, expect } from "vitest";
import { mergeSavedDoc } from "@/utils/saved_doc_merge";

function snapshot<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

/** The document as the builder holds it, and what a save sends. */
function sendSave(live: any) {
  return { sent: snapshot(live), sentRows: [...live.fields] };
}

describe("mergeSavedDoc", () => {
  function form() {
    return {
      name: "f1",
      title: "Survey",
      modified: "2026-10-01 10:00:00",
      fields: [
        { name: "row1", fieldname: "color", fieldtype: "Select", options: "Red\nGreen" },
        { fieldname: "notes", fieldtype: "Data", label: "Notes" },
      ],
    };
  }

  it("keeps the row objects the properties panel is bound to", () => {
    const live = form();
    const selected = live.fields[0];
    const { sent, sentRows } = sendSave(live);
    const server = snapshot(live);
    server.modified = "2026-10-01 10:00:05";

    mergeSavedDoc(live, sent, sentRows, server);

    expect(live.fields[0]).toBe(selected);
    expect(live.modified).toBe("2026-10-01 10:00:05");
  });

  it("keeps an option typed while the save was in flight", () => {
    const live = form();
    const { sent, sentRows } = sendSave(live);
    live.fields[0].options = "Red\nGreen\nBlue"; // typed during the save
    const server = snapshot(sent);

    mergeSavedDoc(live, sent, sentRows, server);

    expect(live.fields[0].options).toBe("Red\nGreen\nBlue");
  });

  it("takes what the server filled in on rows the author did not touch", () => {
    const live = form();
    const { sent, sentRows } = sendSave(live);
    const server = snapshot(sent);
    server.fields[1].name = "row2";
    server.fields[1].target_field = "notes";
    server.fields[1].source_type = "Target Field";

    mergeSavedDoc(live, sent, sentRows, server);

    expect(live.fields[1]).toMatchObject({
      name: "row2",
      target_field: "notes",
      source_type: "Target Field",
    });
  });

  it("keeps a condition added during the save while adopting the new row name", () => {
    const live = form();
    const { sent, sentRows } = sendSave(live);
    (live.fields[1] as any).conditional_logic = '{"action":"Show Field"}';
    const server = snapshot(sent);
    server.fields[1].name = "row2";

    mergeSavedDoc(live, sent, sentRows, server);

    expect((live.fields[1] as any).conditional_logic).toBe('{"action":"Show Field"}');
    expect((live.fields[1] as any).name).toBe("row2");
  });

  it("keeps a field added and the title changed during the save", () => {
    const live = form();
    const { sent, sentRows } = sendSave(live);
    live.title = "Customer Survey";
    live.fields.push({ fieldname: "email", fieldtype: "Email", label: "Email" } as any);
    const server = snapshot(sent);

    mergeSavedDoc(live, sent, sentRows, server);

    expect(live.title).toBe("Customer Survey");
    expect(live.fields.map((f) => f.fieldname)).toEqual(["color", "notes", "email"]);
  });

  it("matches rows by name, not position, when the server reorders them", () => {
    const live = form();
    const { sent, sentRows } = sendSave(live);
    const server = snapshot(sent);
    server.fields = [{ ...server.fields[1], name: "row2" }, { ...server.fields[0], label: "Colour" }];

    mergeSavedDoc(live, sent, sentRows, server);

    expect(live.fields[0].fieldname).toBe("color");
    expect((live.fields[0] as any).label).toBe("Colour");
    expect((live.fields[1] as any).name).toBe("row2");
  });
});
