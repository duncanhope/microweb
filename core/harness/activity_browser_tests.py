"""Interaction checks for the activity lists family on Bootstrap 5 (BS5-10):
Following, Today, Trending and search.

Run with `python manage.py test --tag browser` after one `shoot --record`
(with HARNESS_TOKEN set, for the signed-in pages). Every page is asked for
with ?bs=5, so it renders from core/templates_bs5/.

What reaches the API:
- Nothing, from the search, filter and Following checks: they are GETs from
  the recording, or answered in the browser.
- StopFollowingTests stops following one conversation the harness user
  follows and follows it again with the same email setting, the one write
  the operator allowed. The watchers page has no URL (updates/urls.py), so it
  uses the item's own Follow control, which posts to the same /watchers/
  view. It is recorded once into fixtures/stop-following/ with

      HARNESS_MODE=record HARNESS_WRITE_WATCHER=406745 python manage.py test \\
          --tag browser core.harness.activity_browser_tests.StopFollowingTests

  and replayed from then on. The check fails unless the item ends followed,
  with its email setting as it was.
"""
import os
from urllib.parse import parse_qs, urlsplit

from django.test import override_settings

from core import colors
from core.harness import manifest, recorder
from core.harness.browser_tests import BrowserTestCase
from core.harness.lists_browser_tests import OverlayRecording

LFGSS = manifest.LFGSS
ISLINGTON = 'forum.islington.cc'
ROWS = 'ul.mw-rows > li'
# The conversation lane 8 stops following and follows again: chosen from the
# harness user's watcher list, followed with email off.
WATCHED_CONVERSATION_ID = 406745


class ActivityTestCase(BrowserTestCase):
    """Activity pages ask for Bootstrap 5 with the bs cookie rather than ?bs=5:
    search and Today pass every query parameter on to the search API, so the
    extra one would miss the recording."""

    def open_bs5(self, path, **kwargs):
        return super().open_bs5(path, by_cookie=True, **kwargs)

    def assert_on_bs5(self, page):
        self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'), 'not the Bootstrap 5 base')

    def query(self, page):
        return parse_qs(urlsplit(page.url).query)


class Bs5ActivityPagesTests(ActivityTestCase):

    def test_every_activity_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('activity'):
            with self.subTest(page=p.label):
                page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in)
                self.assert_on_bs5(page)
                self.assertTrue(page.locator('main h1').first.is_visible())
                page.context.close()

    def test_nothing_overflows_on_phones_and_tablets(self):
        for p in manifest.pages_for('activity'):
            for width in (375, 768):
                with self.subTest(page=p.label, width=width):
                    page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in, width=width)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                    page.context.close()


class SearchTests(ActivityTestCase):
    """Lane 7: search from the navbar, then narrow the results."""

    def navbar_search(self, page, words):
        field = page.locator('#navbar-search-input')
        field.fill(words)
        with page.expect_navigation(wait_until='load'):
            field.press('Enter')

    def test_navbar_search_carries_defaults(self):
        page = self.open_bs5('/updates/')
        self.navbar_search(page, 'bike')
        self.assertEqual(urlsplit(page.url).path, '/search/')
        self.assertEqual(self.query(page), {'q': ['bike'], 'defaults': ['true']})
        self.assert_on_bs5(page)
        self.assertEqual(page.locator('main h1').inner_text(), 'Search results for: bike')
        self.assertGreater(page.locator(ROWS).count(), 20)
        # defaults=true is title matches, newest first; the options show it.
        self.assertTrue(page.get_by_label('Title matched search terms').is_checked())
        self.assertTrue(page.get_by_label('Recent updates').is_checked())
        self.assertEqual(page.locator('#navbar-search-input').input_value(), 'bike')
        self.snap(page, 'BS5-10-check-a')

        # A new search from the search page keeps the options, as today.
        self.navbar_search(page, 'wheel')
        self.assertEqual(self.query(page), {'q': ['wheel'], 'inTitle': ['true'], 'sort': ['date']})
        self.assertEqual(page.locator('main h1').inner_text(), 'Search results for: wheel')
        self.assertGreater(page.locator(ROWS).count(), 0)

    def test_a_type_filter_narrows_the_results(self):
        page = self.open_bs5('/search/?q=bike&defaults=true')
        with page.expect_navigation(wait_until='load'):
            page.get_by_label('Conversations').check()
        self.assertEqual(self.query(page), {'q': ['bike'], 'type': ['conversation'], 'inTitle': ['true'],
                                            'sort': ['date']})
        self.assert_on_bs5(page)
        self.assertTrue(page.get_by_label('Conversations').is_checked())
        rows = page.locator(ROWS).count()
        self.assertGreater(rows, 0)
        self.assertEqual(page.locator(ROWS + '[itemtype="http://schema.org/Article"]').count(), rows,
                         'a row that is not a conversation')

    def test_relevancy_and_unticking_leave_out_empty_values(self):
        page = self.open_bs5('/search/?q=bike&defaults=true')
        asked = []

        # Answered here: these searches are not in the recording.
        def answer(route):
            asked.append(route.request.url)
            route.fulfill(status=200, content_type='text/html', body='<p>results</p>')

        page.route(lambda url: urlsplit(url).path == '/search/', answer)
        with page.expect_navigation():
            page.get_by_label('Relevancy').click()  # the stand-in page has no radio to check
        self.assertEqual(parse_qs(urlsplit(asked[-1]).query), {'q': ['bike'], 'inTitle': ['true']})

    def test_today_following_filter(self):
        page = self.open_bs5('/today/', signed_in=True)
        asked = []

        def answer(route):
            asked.append(route.request.url)
            route.fulfill(status=200, content_type='text/html', body='<p>filtered</p>')

        page.route(lambda url: urlsplit(url).path == '/today/', answer)
        with page.expect_navigation():
            page.get_by_label('Following').click()
        self.assertEqual(urlsplit(asked[-1]).query, 'following=true')


# The harness forwards https pages to an http server with X-Forwarded-Proto;
# trusting it lets the Follow control's POST pass Django's CSRF origin check.
@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class StopFollowingTests(ActivityTestCase):
    """Lane 8, live once: stop following a conversation, reload, then follow it
    again with the same email setting. Every step replays from
    fixtures/stop-following/."""

    PATH = '/conversations/%d/' % WATCHED_CONVERSATION_ID

    def setUp(self):
        self.recording = os.path.join(self.fixtures_dir, 'stop-following')
        if self._recorder.mode == recorder.REPLAY:
            if not os.path.isdir(self.recording):
                self.skipTest('No stop following recording in %s. Record it once: HARNESS_MODE=record '
                              'HARNESS_WRITE_WATCHER=%d python manage.py test --tag browser '
                              'core.harness.activity_browser_tests.StopFollowingTests'
                              % (self.recording, WATCHED_CONVERSATION_ID))
        elif os.environ.get('HARNESS_WRITE_WATCHER') != str(WATCHED_CONVERSATION_ID):
            self.skipTest('Recording stops the harness user following conversation %d; set '
                          'HARNESS_WRITE_WATCHER=%d to allow it.' % (WATCHED_CONVERSATION_ID, WATCHED_CONVERSATION_ID))

    def step(self, name):
        return OverlayRecording(self._recorder, self.fixtures_dir, os.path.join('stop-following', name))

    def control(self, page):
        return page.locator('#mw-metabar [data-mw-subscribe]')

    def state(self, page):
        control = self.control(page)
        return control.get_attribute('data-state'), control.locator('input[name=emailme]').is_checked()

    def load(self, page):
        page.goto('https://%s%s' % (LFGSS, self.PATH), wait_until='load')
        self.assert_on_bs5(page)
        page.wait_for_function('() => window.bootstrap')

    def toggle(self, page, button, state):
        with page.expect_response(lambda r: urlsplit(r.url).path == '/watchers/' and r.request.method == 'POST') as sent:
            self.control(page).get_by_role('button', name=button).click()
        self.assertEqual(sent.value.status, 200)
        page.wait_for_function('(s) => document.querySelector("#mw-metabar [data-mw-subscribe]").dataset.state === s',
                               arg=state)
        return parse_qs(sent.value.request.post_data)

    def test_stop_following_and_follow_again(self):
        page = self.new_page(signed_in=True)
        page.context.add_cookies([{'name': 'bs', 'value': '5', 'url': 'https://%s/' % LFGSS}])

        with self.step('0-before'):
            self.load(page)
            watched, email = self.state(page)
            self.assertEqual(watched, 'on', 'the harness user no longer follows the lane 8 conversation')

        with self.step('1-unfollowed'):
            posted = self.toggle(page, 'unfollow', 'off')
            self.assertEqual((posted['delete'], posted['itemType'], posted['itemId']),
                             (['true'], ['conversation'], [str(WATCHED_CONVERSATION_ID)]))
            self.load(page)
            self.assertEqual(self.state(page)[0], 'off', 'still following after a reload')
            self.snap(page, 'BS5-10-check-b')

        with self.step('2-followed'):
            posted = self.toggle(page, 'Follow', 'on')
            self.assertNotIn('delete', posted)
            self.load(page)
            self.assertEqual(self.state(page)[0], 'on')

        if self.state(page)[1] != email:
            with self.step('3-email'):
                with page.expect_response(lambda r: urlsplit(r.url).path == '/watchers/'):
                    self.control(page).locator('input[name=emailme]').set_checked(email)
                self.load(page)

        # A fresh load, not the page the last click left.
        with self.step('4-verified'):
            self.load(page)
            self.assertEqual(self.state(page), ('on', email), 'the follow or its email setting was not put back')


class SignedInFollowingTests(ActivityTestCase):
    """Lane 9: Following as the harness user."""

    def test_following_signed_in(self):
        page = self.open_bs5('/updates/', signed_in=True)
        nav = page.locator('.mw-nav .nav-link[aria-current=page]')
        self.assertEqual(nav.inner_text(), 'Following')
        rows = page.locator(ROWS)
        self.assertGreaterEqual(rows.count(), 20)
        self.assertGreater(page.locator(ROWS + ' .badge.text-bg-warning').count(), 0, 'no NEW badges')
        self.assertEqual(page.locator('#mw-metabar').get_by_role('link', name='Update notification settings')
                         .get_attribute('href'), '/updates/settings/')
        # Rows link members to the newest comment.
        self.assertRegex(page.locator(ROWS + ' .mw-row-title a').first.get_attribute('href'),
                         r'^/(conversations|events|huddles)/\d+/newest/$')
        # A message row's participants have tooltips. Whether the first page
        # has a message row depends on the recording (the 2026-09-30 evening one
        # has none), so this part runs only when it does.
        participants = page.locator(ROWS + ' .mw-participants a')
        with self.subTest('participant tooltips'):
            if not participants.count():
                self.skipTest('No message row on the recorded first page of Following.')
            participant = participants.first
            participant.hover()
            page.locator('.tooltip.show').wait_for()
            self.assertEqual(page.locator('.tooltip.show').inner_text(),
                             participant.get_attribute('data-bs-original-title'))
            page.mouse.move(0, 0)
        self.assertEqual(page.locator('.mw-list-header .mw-page-jump').count(), 1)
        self.snap(page, 'BS5-10-signed-in')

        with page.expect_navigation(wait_until='load'):
            page.locator('#mw-metabar').get_by_role('link', name='Update notification settings').click()
        self.assertEqual(urlsplit(page.url).path, '/updates/settings/')
        self.assert_on_bs5(page)

    def test_following_as_a_guest(self):
        page = self.open_bs5('/updates/')
        self.assertIn('Please sign in to view updates', page.locator('main').inner_text())
        self.assertEqual(page.locator(ROWS).count(), 0)
        self.assertEqual(page.get_by_role('link', name='Update notification settings').count(), 0)

    def test_today_signed_in_shows_messages(self):
        page = self.open_bs5('/today/', signed_in=True)
        self.assertEqual(page.locator('.mw-nav .nav-link[aria-current=page]').inner_text(), 'Today')
        self.assertGreater(page.locator(ROWS).count(), 0)
        self.assertTrue(page.get_by_label('Following').is_visible())


# Colour facts on an activity page: the surround, the content and its links.
COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  const rowLink = document.querySelector('ul.mw-rows .mw-row-meta a');
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    title: rgb(document.querySelector('main h1'), 'color'),
    link: rgb(document.querySelector('.mw-breadcrumb a'), 'color'),
    rowLink: rowLink ? rgb(rowLink, 'color') : null,
    footerLink: rgb(document.querySelector('.mw-footer a'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
  };
}"""


class IslingtonBrandingTests(ActivityTestCase):
    """Lane 10: Site branding holds on Today and search in light and dark."""

    def test_islington_activity_light_and_dark(self):
        site_link = colors.parse_hex('#185945')
        surround = colors.parse_hex('#bfc3c5')
        for label, path in (('today', '/today/'), ('search', '/search/?q=ride&defaults=true')):
            for mode in ('light', 'dark'):
                with self.subTest(page=label, mode=mode):
                    page = self.open_bs5(path, host=ISLINGTON, color_mode=mode)
                    facts = page.evaluate(COLOR_FACTS_JS)
                    self.assertEqual(facts['theme'], mode)
                    self.assertEqual(tuple(facts['surround']), surround, 'the Site surround')
                    self.assertEqual(facts['logo'], 89)
                    self.assertGreaterEqual(colors.contrast(facts['title'], facts['main']), 7)
                    links = [facts['link'], facts['footerLink']] + ([facts['rowLink']] if facts['rowLink'] else [])
                    if label == 'search':
                        self.assertIsNotNone(facts['rowLink'], 'no row links on the search page')
                    for link in links:
                        if mode == 'light':
                            self.assertEqual(tuple(link), site_link)
                        else:
                            self.assertGreaterEqual(colors.contrast(link, facts['main']), colors.AA)
                    if mode == 'dark':
                        self.assertGreaterEqual(colors.contrast(facts['footerLink'], colors.dark_panel(surround)),
                                                colors.AA)
                    self.snap(page, 'BS5-10-branding-%s-%s' % (label, mode))
                    page.context.close()
