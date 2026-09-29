"""
What happens to a file a visitor uploads through a form.

Frappe refuses a private file to a guest outright: `download_private_file`
raises Forbidden for the Guest user before any permission check runs, and a
`has_permission` hook cannot help, because hooks may only deny access, never
grant it. So a visitor who attached a document or dropped a video into a rich
text answer could not see back the thing they had just uploaded -- the preview,
the video player and the link all answered 403.

The only way a visitor can read their own upload is for the file to be public.
A public file is served from `/files/<name>` with no permission check at all,
so its name is the only thing between the file and anyone who guesses it -- and
Frappe adds a random suffix only when the name is already taken, which left
"research person and company.mp4" sitting at an entirely predictable URL. Every
file uploaded through a form therefore gets a random prefix: readable to the
person holding the link, not worth guessing for anyone else.

This is done by overriding the File class rather than with a doc event, because
`File.before_insert` writes the content to disk and fixes `file_url` -- and a
hooked `before_insert` runs *after* the controller's own, by which time the
file is already saved under its original name. (`before_naming` is no earlier:
`Document.insert` names the document after calling `before_insert`.) Renaming
at either point only produces "The File URL you've entered is incorrect".
"""

import os

import frappe
from frappe.core.doctype.file.file import File

#: Uploads from a form are filed under this doctype -- it is what the guest
#: upload allowlist in System Settings is keyed on -- which is also how they
#: are recognised here.
FORM_UPLOAD_DOCTYPE = "FP Form Submission"

#: Long enough that guessing is not worth attempting, short enough to keep the
#: URL readable.
PREFIX_LENGTH = 10


def is_form_upload(doc) -> bool:
    """Whether this file is being uploaded through a Forms Pro form."""
    return (
        doc.attached_to_doctype or frappe.form_dict.get("doctype")
    ) == FORM_UPLOAD_DOCTYPE


def already_prefixed(file_name: str) -> bool:
    """True for a name this has already renamed, so a re-save does not stack tokens."""
    stem = os.path.splitext(file_name)[0]
    return (
        len(stem) > PREFIX_LENGTH
        and stem[PREFIX_LENGTH] == "-"
        and stem[:PREFIX_LENGTH].isalnum()
    )


def public_upload_name(file_name: str) -> str:
    if already_prefixed(file_name):
        return file_name
    return f"{frappe.generate_hash(length=PREFIX_LENGTH)}-{file_name}"


class FormsProFile(File):
    """
    A File that knows about form uploads.

    Every other file on the site behaves exactly as before: the branch below is
    the only difference, and it is taken only for uploads a form made.
    """

    def before_insert(self):
        if is_form_upload(self) and self.file_name and not self.file_url:
            self.file_name = public_upload_name(self.file_name)
            # Private would be safer, but Frappe will not serve a private file
            # to a guest at all, and the visitor has to be able to see what
            # they just attached.
            self.is_private = 0

        super().before_insert()
