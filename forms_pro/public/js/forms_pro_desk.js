// Forms Pro: fix opening Form doctype documents from list view.
// The doctype name "Form" conflicts with the router's "form" view, so path-based
// navigation (/desk/form/docname) is misinterpreted. We patch set_route so that
// when called with a path like "/desk/form/<name>" we use ["Form", "Form", name].
(function () {
    if (typeof frappe === "undefined") return;

    const original_set_route = frappe.set_route;
    frappe.set_route = function () {
        const args = Array.from(arguments);
        if (args.length === 1 && typeof args[0] === "string" && args[0].includes("/")) {
            // Path string: e.g. "/desk/form/n8tqgeco1u" or "form/n8tqgeco1u"
            // Only match form/<docname> (one segment), not form/view/list etc.
            const m = args[0].match(/(?:^\/?(?:desk\/|app\/)?)?form\/([^/#?]+)(?=[#?]|$)/);
            if (m) {
                return original_set_route.apply(frappe.router, ["Form", "Form", m[1]]);
            }
        }
        return original_set_route.apply(frappe.router, args);
    };
})();

// Forms Pro: link a record back to the submission that created it.
//
// A record created by a form carries `fp_linked_form`. Fields that exist on the
// target DocType are written onto the record, but everything else lives only in
// the submission payload -- so from the desk there was no way to see the full
// set of answers, or even to tell the record came from a form. This adds a
// toolbar button on any such record that opens the submission in Forms Pro.
(function () {
    if (typeof frappe === "undefined" || typeof $ === "undefined") return;

    const BUTTON_LABEL = __("View Submission");

    $(document).on("form-refresh", function (e, frm) {
        if (!frm || !frm.doc || frm.is_new()) return;
        // Cheap guard: only records stamped by Forms Pro qualify.
        if (!frm.doc.fp_linked_form) return;
        // `add_custom_button` de-duplicates by label, but the async call below
        // would still fire on every refresh.
        if (frm.__fp_submission_link_added) return;
        frm.__fp_submission_link_added = true;

        frappe.call({
            method: "forms_pro.api.submission.get_submission_for_document",
            args: { doctype: frm.doc.doctype, docname: frm.doc.name },
            callback: function (r) {
                const info = r && r.message;
                if (!info || !info.form) return;

                let url = "/forms/manage/" + encodeURIComponent(info.form) + "/submissions";
                if (info.submission) {
                    url += "?submission=" + encodeURIComponent(info.submission);
                }

                frm.add_custom_button(BUTTON_LABEL, function () {
                    window.open(url, "_blank");
                });
                // The link has to point at the submission, not the form: the
                // form is the template, the submission is what this particular
                // record was created from, and it is where every answer lives
                // -- including the ones that are not fields on this DocType.
                const label = frappe.utils.escape_html(info.form_title || info.form);
                frm.set_intro(
                    info.submission
                        ? __("Submitted through {0}. Open the submission to see every answer.", [
                              label,
                          ])
                        : __("Created from the form {0}.", [label]),
                    "blue"
                );
            },
        });
    });
})();
