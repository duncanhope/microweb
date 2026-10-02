"""The Bootstrap 3 membership group form in Chromium, with a group name,
a criterion and a member that all hold markup. They show as typed and run
nothing. Needs no recording: the page is rendered here and every other
request is refused. Every group, criterion and person is made up."""
import mimetypes
import os
from unittest import SkipTest

from django.conf import settings
from django.test import SimpleTestCase, tag

from core.tests.test_membership_form import NASTY, edit_page

STATIC_ROOT = os.path.join(os.path.dirname(settings.PROJECT_ROOT), 'core', 'static')
ORIGIN = 'https://lfgss.test'


@tag('browser')
class MembershipFormBrowserTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise SkipTest('Browser checks need: pip install -r requirements-dev.txt')
        cls.html = edit_page()
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._playwright.stop()
        super().tearDownClass()

    def route(self, route):
        path = route.request.url[len(ORIGIN):].split('?')[0]
        if route.request.url.startswith(ORIGIN) and path == '/':
            return route.fulfill(body=self.html, content_type='text/html')
        if route.request.url.startswith(ORIGIN) and path.startswith('/static/'):
            local = os.path.normpath(os.path.join(STATIC_ROOT, path[len('/static/'):]))
            if local.startswith(STATIC_ROOT) and os.path.isfile(local):
                return route.fulfill(path=local, content_type=mimetypes.guess_type(local)[0])
        return route.abort()

    def test_markup_in_the_group_shows_as_text(self):
        page = self._browser.new_page()
        dialogs = []
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/*', self.route)
        page.goto(ORIGIN + '/')
        page.wait_for_function('typeof jQuery !== "undefined" && typeof role !== "undefined"')

        self.assertEqual(dialogs, [])
        self.assertEqual(page.locator('#name').input_value(), NASTY)
        self.assertEqual(page.locator('.criteria-list .form-widget-list strong').all_text_contents(), [NASTY, NASTY])
        self.assertEqual(page.locator('.criteria-list script').count(), 0)
        self.assertEqual(page.evaluate('role.mappings.name.value'), NASTY)
        self.assertFalse([e for e in errors if 'alert' in e], errors)
        page.close()
