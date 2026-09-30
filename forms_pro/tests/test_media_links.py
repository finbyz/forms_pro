"""
A video in a rich text answer has to be reachable from the desk.

The element itself survives storage untouched; the desk is where it vanishes,
because the Text Editor control there parses the HTML with an editor that has
no video node. A plain link beside it is something every renderer keeps.
"""

from frappe.tests.utils import FrappeTestCase

from forms_pro.utils.media_links import LINK_CLASS, add_media_links

VIDEO = '<video src="/files/abc1234567-my clip.mp4" controls></video>'


class TestAddMediaLinks(FrappeTestCase):
    def test_content_without_media_is_returned_untouched(self):
        for unchanged in (None, "", "<p>just words</p>", "<img src='/files/x.png'>"):
            self.assertEqual(add_media_links(unchanged), unchanged)

    def test_a_link_is_added_after_a_video(self):
        out = add_media_links(VIDEO)
        self.assertIn(LINK_CLASS, out)
        self.assertIn('href="/files/abc1234567-my clip.mp4"', out)
        self.assertLess(out.index("<video"), out.index("<a "), "the link belongs after the video")

    def test_the_video_element_is_kept(self):
        """Anything that can play it still should; only the desk cannot."""
        self.assertIn("<video", add_media_links(VIDEO))

    def test_the_link_is_labelled_with_the_file_name(self):
        self.assertIn(">my clip.mp4<", add_media_links(VIDEO).replace("abc1234567-", ""))

    def test_a_source_element_is_read_when_there_is_no_src(self):
        out = add_media_links(
            '<video><source src="/files/clip.webm" type="video/webm"></video>'
        )
        self.assertIn('href="/files/clip.webm"', out)

    def test_audio_is_handled_too(self):
        self.assertIn('href="/files/note.mp3"', add_media_links('<audio src="/files/note.mp3"></audio>'))

    def test_running_twice_does_not_add_a_second_link(self):
        once = add_media_links(VIDEO)
        self.assertEqual(add_media_links(once), once)

    def test_a_placeholder_with_no_source_is_left_alone(self):
        """An upload that failed leaves an empty node; there is nothing to link to."""
        placeholder = '<video width="640" height="480" controls=""></video>'
        self.assertEqual(add_media_links(placeholder), placeholder)


class TestEmbeddedVideoLinks(FrappeTestCase):
    """
    An embedded video arrives as an <iframe>, and Frappe's sanitiser deletes
    iframes when the record is saved -- the answer kept nothing, not even the
    address. It must leave a link that survives.
    """

    YOUTUBE = (
        '<iframe src="https://www.youtube.com/embed/yIW67YKD_Vk?rel=0&amp;modestbranding=1"'
        ' width="640" height="360"></iframe>'
    )

    def test_a_youtube_embed_leaves_a_watch_link(self):
        out = add_media_links(self.YOUTUBE)
        self.assertIn('href="https://www.youtube.com/watch?v=yIW67YKD_Vk"', out)

    def test_a_vimeo_embed_leaves_a_page_link(self):
        out = add_media_links('<iframe src="https://player.vimeo.com/video/76979871"></iframe>')
        self.assertIn('href="https://vimeo.com/76979871"', out)

    def test_the_link_survives_the_sanitiser(self):
        """The whole point: the iframe goes, the address stays."""
        from frappe.utils.html_utils import sanitize_html

        stored = sanitize_html(add_media_links(self.YOUTUBE))
        self.assertNotIn("<iframe", stored)
        self.assertIn("https://www.youtube.com/watch?v=yIW67YKD_Vk", stored)
