"""Interaction checks for the Bootstrap 5 base (BS5-05).

No family renders on the new base yet, so these render /about/terms/ with a
stand-in page, core/harness/bs5_pages/legal.html, added to the front of the
bs5 template engine for the duration of the tests. Run with
`python manage.py test --tag browser` after one `shoot --record`.

Nothing here reaches the API with a write: the Follow check answers the
watcher POST in the browser.
"""
import copy
import os
import re
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.test import override_settings

from core.harness import manifest
from core.harness.browser_tests import BrowserTestCase

HARNESS_PAGES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bs5_pages')
PAGE = 'https://%s/about/terms/?bs=5' % manifest.LFGSS


def _with_harness_pages():
    templates = copy.deepcopy(settings.TEMPLATES)
    bs5 = next(t for t in templates if t.get('NAME') == 'bs5')
    bs5['DIRS'] = [HARNESS_PAGES] + list(bs5['DIRS'])
    return templates


# Every keyboard-reachable control should show Bootstrap's focus ring.
FOCUS_RING_JS = """() => {
  const el = document.activeElement;
  const s = getComputedStyle(el);
  return {
    tag: el.tagName, text: (el.innerText || el.getAttribute('aria-label') || el.placeholder || '').trim(),
    inNav: !!el.closest('.mw-header, .mw-nav'),
    ring: s.boxShadow !== 'none' || (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0),
  };
}"""


@override_settings(TEMPLATES=_with_harness_pages(), BS5_TEMPLATE_DIR=HARNESS_PAGES)
class BaseLayoutTests(BrowserTestCase):

    def open(self, width=1280, signed_in=False):
        page = self.new_page(width=width, signed_in=signed_in)
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        # Off-site requests the recording lacks are aborted by design; only
        # script errors count.
        page.on('console', lambda msg: errors.append(msg.text)
                if msg.type == 'error' and not msg.text.startswith('Failed to load resource') else None)
        page.goto(PAGE, wait_until='load')
        page.wait_for_function('() => window.bootstrap && document.querySelector("time#harness-time").title')
        self.addCleanup(lambda: self.assertEqual(errors, [], 'script errors on the page'))
        return page

    def assert_focus_stays_in(self, page, selector, presses=15):
        for _ in range(presses):
            page.keyboard.press('Tab')
            inside = page.evaluate('(s) => document.querySelector(s).contains(document.activeElement)', selector)
            self.assertTrue(inside, 'focus left %s' % selector)

    # Layout ------------------------------------------------------------------

    def test_desktop_layout(self):
        page = self.open(1280)
        logo = page.locator('.mw-logo img').bounding_box()
        account = page.locator('.mw-account').bounding_box()
        self.assertLess(logo['x'], account['x'], 'account box right of the logo')
        self.assertEqual(logo['height'], 89)
        links = page.locator('.mw-nav .navbar-nav .nav-link').first.bounding_box()
        search = page.locator('.mw-search').bounding_box()
        self.assertGreater(search['x'], links['x'], 'search right of the nav links')
        self.assertAlmostEqual(search['y'], links['y'], delta=10)
        content = page.locator('main').bounding_box()
        metabar = page.locator('#mw-metabar').bounding_box()
        self.assertAlmostEqual(content['width'] / (content['width'] + metabar['width']), .75, places=2)
        self.assertAlmostEqual(content['y'], metabar['y'], delta=1)
        self.assertFalse(page.locator('.mw-drawer-btn').first.is_visible())
        self.snap(page, 'base-1280')

    def test_mobile_header(self):
        page = self.open(375)
        menu = page.locator('#mw-menu-btn').bounding_box()
        logo = page.locator('.mw-logo img').bounding_box()
        side = page.locator('#mw-metabar-btn').bounding_box()
        self.assertLess(menu['x'] + menu['width'], logo['x'])
        self.assertLess(logo['x'] + logo['width'], side['x'])
        self.assertFalse(page.locator('.mw-account').is_visible())
        self.assertFalse(page.locator('#mw-metabar').is_visible())
        self.snap(page, 'base-375')

    # Drawers ------------------------------------------------------------------

    def open_overlay(self, page, trigger, target):
        """Click `trigger` and wait until Bootstrap has finished showing `target`."""
        page.evaluate("""(t) => {
          const el = document.querySelector(t);
          delete el.dataset.shown;
          for (const type of ['shown.bs.offcanvas', 'shown.bs.modal']) {
            el.addEventListener(type, () => { el.dataset.shown = 'yes'; }, { once: true });
          }
        }""", target)
        page.locator(trigger).click()
        page.locator(target + '[data-shown]').wait_for()

    def check_drawer(self, page, button, drawer, name):
        self.open_overlay(page, button, drawer)
        self.snap(page, name)
        self.assert_focus_stays_in(page, drawer)
        page.keyboard.press('Escape')
        page.locator(drawer).wait_for(state='hidden')
        self.assertTrue(page.evaluate('(s) => document.activeElement === document.querySelector(s)', button),
                        'focus returns to the drawer button')

    def test_menu_drawer_opens_traps_focus_and_closes_on_escape(self):
        page = self.open(375)
        self.check_drawer(page, '#mw-menu-btn', '#mw-menu', 'base-drawer-menu')

    def test_metabar_drawer_opens_traps_focus_and_closes_on_escape(self):
        page = self.open(375)
        self.check_drawer(page, '#mw-metabar-btn', '#mw-metabar', 'base-drawer-metabar')

    def test_member_header_and_menu_drawer(self):
        page = self.open(1280, signed_in=True)
        account = page.locator('.mw-account')
        self.assertIn('Messages', account.inner_text())
        self.assertTrue(account.locator('#logout').is_visible())
        self.assertEqual(page.locator('#modal-signin').count(), 0)
        self.snap(page, 'base-member-1280')
        page.set_viewport_size({'width': 375, 'height': 900})
        self.open_overlay(page, '#mw-menu-btn', '#mw-menu')
        drawer = page.locator('#mw-menu').inner_text()
        for text in ('Messages', 'Your account', 'Edit profile', 'Sign out'):
            self.assertIn(text, drawer)
        self.snap(page, 'base-member-drawer')

    # Sign in ------------------------------------------------------------------

    def wait_for_lock_email(self, page):
        email = page.locator('.auth0-lock input[type=email], .auth0-lock input[name=email]').first
        email.wait_for(state='visible', timeout=15000)
        return email

    def test_signin_modal_hands_off_to_lock(self):
        page = self.open(1280)
        self.open_overlay(page, '#harness-modal', '#modal-signin')
        modal = page.locator('#modal-signin')
        self.snap(page, 'base-modal')
        modal.locator('.modal-body .btn').click()
        modal.wait_for(state='hidden')
        email = self.wait_for_lock_email(page)
        email.click()
        page.keyboard.type('harness@example.com')
        self.assertEqual(email.input_value(), 'harness@example.com')
        self.assertFalse(page.evaluate('document.body.classList.contains("modal-open")'))
        self.snap(page, 'base-lock')

    def test_navbar_signin_opens_lock_directly(self):
        page = self.open(1280)
        page.locator('#login').click()
        email = self.wait_for_lock_email(page)
        self.assertFalse(page.locator('#modal-signin').is_visible())
        email.click()
        page.keyboard.type('harness@example.com')
        self.assertEqual(email.input_value(), 'harness@example.com')
        self.snap(page, 'base-lock-navbar')

    # base.js ------------------------------------------------------------------

    def test_tooltip(self):
        page = self.open(1280)
        page.locator('#harness-tooltip').hover()
        tip = page.locator('.tooltip.show')
        tip.wait_for()
        self.assertEqual(tip.inner_text().strip(), 'A Bootstrap 5 tooltip')
        self.snap(page, 'base-tooltip')

    def test_relative_times(self):
        page = self.open(1280)
        time = page.locator('#harness-time')
        self.assertRegex(time.inner_text(), r'^\d+ years ago$')
        self.assertRegex(time.get_attribute('title'), r'^Sun, Jan 18, 2009')
        self.assertEqual(page.locator('#harness-time-plain').inner_text(), '18 Jan 2009')

        # Intl.RelativeTimeFormat's English output for each of moment.js's buckets.
        cases = [
            (timedelta(seconds=-10), 'now'),
            (timedelta(minutes=-1), '1 minute ago'),
            (timedelta(minutes=-5), '5 minutes ago'),
            (timedelta(hours=-3), '3 hours ago'),
            (timedelta(days=-1), '1 day ago'),
            (timedelta(days=-2), '2 days ago'),
            (timedelta(days=-91), '3 months ago'),
            (timedelta(days=-730), '2 years ago'),
            (timedelta(days=3), 'in 3 days'),
        ]
        stamps = [(self.frozen + delta).isoformat().replace('+00:00', 'Z') for delta, _ in cases]
        texts = page.evaluate("""async (stamps) => {
          const list = document.getElementById('harness-checks');
          const made = stamps.map((s) => {
            const t = document.createElement('time');
            t.setAttribute('datetime', s);
            list.append(t);
            return t;
          });
          (await import('/static/js/bs5/base.js')).updateTimes();
          return made.map((t) => t.textContent);
        }""", stamps)
        self.assertEqual(texts, [expected for _, expected in cases])
        self.snap(page, 'base-time')

        # Clicking a time shows absolute times, and clicking again goes back.
        time.click()
        self.assertRegex(time.inner_text(), r'^Sun, Jan 18, 2009')
        time.click()
        self.assertRegex(time.inner_text(), r'^\d+ years ago$')

    def test_stats_code_and_page_jump(self):
        page = self.open(1280)
        stat = page.locator('span[stat]')
        self.assertEqual(stat.inner_text(), '1.23M')
        self.assertEqual(stat.get_attribute('title'), '1,234,567 comments')
        page.locator('pre.prettyprinted').wait_for()

        field = page.locator('form[name=paginationByOffset] input[type=text]')
        field.fill('3')
        with page.expect_navigation(wait_until='load'):
            field.blur()
        url = urlsplit(page.url)
        self.assertEqual(url.path, '/about/terms/')
        self.assertEqual(parse_qs(url.query).get('offset'), ['50'])

    def test_follow_posts_to_the_watcher_view(self):
        page = self.open(1280)
        posts = []

        def answer(route):
            posts.append(parse_qs(route.request.post_data))
            route.fulfill(status=200, body='')

        page.route(re.compile(r'.*/watchers/$'), answer)
        control = page.locator('[data-mw-subscribe]')
        self.assertEqual(control.get_attribute('data-state'), 'off')
        control.locator('[data-mw-subscribe-toggle]').click()
        page.wait_for_function('document.querySelector("[data-mw-subscribe]").dataset.state === "on"')
        control.locator('input[name=emailme]').check()
        control.locator('[data-mw-subscribe-toggle]').click()
        page.wait_for_function('document.querySelector("[data-mw-subscribe]").dataset.state === "off"')

        self.assertEqual(len(posts), 3)
        follow, email, unfollow = posts
        self.assertEqual({k: follow[k] for k in ('itemId', 'itemType', 'updateTypeId')},
                         {'itemId': ['141600'], 'itemType': ['conversation'], 'updateTypeId': ['1']})
        self.assertTrue(follow['csrfmiddlewaretoken'][0])
        self.assertEqual((email['patch'], email['emailMe']), (['true'], ['true']))
        self.assertEqual(unfollow['delete'], ['true'])

    # Focus -----------------------------------------------------------------------

    def test_focus_ring_on_every_header_and_nav_control(self):
        page = self.open(1280)
        page.locator('.mw-logo').focus()
        seen = []
        for _ in range(20):
            state = page.evaluate(FOCUS_RING_JS)
            if not state['inNav']:
                break
            seen.append(state)
            if state['text'] == 'Today':
                self.snap(page, 'base-focus')
            page.keyboard.press('Tab')
        labels = [s['text'] for s in seen]
        for expected in ('Sign In or Register', 'Forums', 'Today', 'People', 'Search'):
            self.assertIn(expected, labels)
        missing = [s['text'] or s['tag'] for s in seen if not s['ring']]
        self.assertEqual(missing, [], 'controls without a visible focus ring')
