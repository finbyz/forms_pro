"""
Make media inside a rich text answer reachable from the desk.

A visitor can drop a video into a Text Editor field and it stores fine -- the
`<video>` element survives Frappe's sanitiser untouched. The desk is where it
disappears: the Text Editor control there parses the stored HTML with its own
editor, which has no video node, so the element is dropped on the way in. The
answer looks empty and the file appears nowhere, even though it is sitting in
the File list.

Rather than fight the desk's editor, every media element gets a plain link to
the same file placed after it. The link is ordinary HTML that every renderer
keeps, so whoever opens the record can click straight through to the video --
and the `<video>` element stays where it is, so the form's own success page and
any other viewer that can play it still do.
"""

import os
import urllib.parse

from bs4 import BeautifulSoup

#: Elements that carry a file the desk will not render.
MEDIA_TAGS = ("video", "audio", "embed")

#: Marks the links this adds, so running twice does not double them up.
LINK_CLASS = "fp-media-link"


def _source_url(element) -> str | None:
    """The file a media element points at, whether inline or in a <source>."""
    url = (element.get("src") or "").strip()
    if url:
        return url

    source = element.find("source")
    return ((source.get("src") or "").strip() or None) if source else None


def _label_for(url: str) -> str:
    """The file's own name, which is more use than the raw path."""
    name = os.path.basename(urllib.parse.urlparse(url).path)
    return urllib.parse.unquote(name) or url


def add_media_links(html: str | None) -> str | None:
    """
    Return the HTML with a clickable link after every video or audio element.

    Anything without media is returned unchanged, including None and "", so
    this is safe to run over every rich text answer.
    """
    if not html or not any(f"<{tag}" in html.lower() for tag in MEDIA_TAGS):
        return html

    soup = BeautifulSoup(html, "html.parser")
    changed = False

    for element in soup.find_all(MEDIA_TAGS):
        url = _source_url(element)
        if not url:
            continue

        # Already linked, either by an earlier run or by the author.
        following = element.find_next_sibling()
        if following and following.find("a", href=url):
            continue

        paragraph = soup.new_tag("p")
        anchor = soup.new_tag("a", href=url, target="_blank", rel="noopener")
        anchor["class"] = [LINK_CLASS]
        anchor.string = _label_for(url)
        paragraph.append(anchor)
        element.insert_after(paragraph)
        changed = True

    return str(soup) if changed else html
