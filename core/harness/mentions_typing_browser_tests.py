"""@mentions while typing on: what the list shows between a keystroke and
the API's answer for it. Needs no recording: the member search is a made-up
one in the page, slow on purpose, and every other request is refused. The
members are made up.

Typing @ab showed the ab members; typing e kept showing all of them until
the debounce and the API's answer for abe had both passed, so Enter in that
time inserted a member who did not match. And the list the answer then drew
had no member highlighted, though Enter still picked the first."""
import os
from urllib.parse import urlsplit
from unittest import SkipTest

from django.conf import settings
from django.test import SimpleTestCase, tag

SCRIPTS = os.path.join(os.path.dirname(settings.PROJECT_ROOT), 'core', 'static', 'js', 'bs5')
ORIGIN = 'https://lfgss.test'
API_DELAY_MS = 600

PAGE = '''<!doctype html><meta name="subdomain" content="https://api.lfgss.test"><body>
<textarea id="box" style="width:400px;height:120px"></textarea>
<script>
const MEMBERS = ['abcccc', 'abdddd', 'abeeee', 'abffff', 'abgggg'];
window.asked = [];
window.fetch = (url, {signal} = {}) => new Promise((resolve, reject) => {
  const q = new URL(url).searchParams.get('q');
  asked.push(q);
  const timer = setTimeout(() => {
    const items = MEMBERS.filter((name) => name.startsWith(q)).map((profileName, id) => ({id, profileName, avatar: ''}));
    resolve(new Response(JSON.stringify({profiles: {items}})));
  }, %d);
  signal?.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')); });
});
</script>
<script type="module">
import { attachMentions } from '/static/js/bs5/mentions.js';
attachMentions(document.getElementById('box'), {apiBase: 'https://api.lfgss.test'});
window.ready = true;
</script>''' % API_DELAY_MS


@tag('browser')
class MentionsTypingBrowserTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise SkipTest('Browser checks need: pip install -r requirements-dev.txt')
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._playwright.stop()
        super().tearDownClass()

    def route(self, route):
        url = urlsplit(route.request.url)
        if url.netloc != urlsplit(ORIGIN).netloc:
            return route.abort()
        if url.path == '/':
            return route.fulfill(body=PAGE, content_type='text/html')
        if url.path == '/static/js/bs5/mentions.js':
            return route.fulfill(path=os.path.join(SCRIPTS, 'mentions.js'), content_type='text/javascript')
        return route.abort()

    def open(self):
        page = self._browser.new_page()
        self.addCleanup(page.close)
        page.route('**/*', self.route)
        page.goto(ORIGIN + '/')
        page.wait_for_function('window.ready')
        box = page.locator('#box')
        box.click()
        return page, box

    def options(self, page):
        return page.locator('.mw-mentions [role=option]')

    def test_the_list_narrows_as_soon_as_a_letter_is_typed(self):
        page, box = self.open()
        box.press_sequentially('@ab', delay=20)
        self.options(page).first.wait_for()
        self.assertEqual(self.options(page).all_text_contents(),
                         ['@abcccc', '@abdddd', '@abeeee', '@abffff', '@abgggg'])

        box.press('e')
        # Well before the debounce and the API's answer for abe.
        self.assertEqual(self.options(page).all_text_contents(), ['@abeeee'])
        self.assertEqual(box.get_attribute('aria-activedescendant'), self.options(page).first.get_attribute('id'))
        box.press('Enter')
        self.assertEqual(box.input_value(), '@abeeee ')

    def test_the_answer_for_the_latest_letters_is_highlighted(self):
        page, box = self.open()
        box.press_sequentially('@ab', delay=20)
        self.options(page).first.wait_for()
        box.press('e')
        page.wait_for_function("asked.includes('abe')")
        page.wait_for_timeout(API_DELAY_MS + 200)
        self.assertEqual(self.options(page).all_text_contents(), ['@abeeee'])
        first = self.options(page).first
        self.assertEqual(first.get_attribute('aria-selected'), 'true')
        self.assertIn('active', first.get_attribute('class'))

    def test_a_letter_no_shown_member_matches_waits_for_the_api(self):
        page, box = self.open()
        box.press_sequentially('@ab', delay=20)
        self.options(page).first.wait_for()
        box.press('z')
        # None of the five shown match abz: nothing to pick from yet.
        self.assertEqual(self.options(page).count(), 0)
        box.press('Enter')
        self.assertEqual(box.input_value(), '@abz\n')
