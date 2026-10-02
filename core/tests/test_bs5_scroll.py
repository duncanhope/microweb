"""Bootstrap 5 turns on smooth scrolling for the whole page, so following a
link to a comment (or to #reply) glided down the thread instead of opening
there. Bootstrap 3 jumped straight to it, and so does Bootstrap 5 now."""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

CSS = Path(settings.PROJECT_ROOT).parent / 'core' / 'static' / 'themes' / '1' / 'css' / 'bs5.min.css'


class InstantScrollTests(SimpleTestCase):

    def test_the_page_does_not_scroll_smoothly(self):
        self.assertNotIn('scroll-behavior:smooth', CSS.read_text())
