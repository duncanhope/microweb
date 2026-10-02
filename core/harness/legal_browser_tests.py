"""Interaction checks for the legal and error pages on Bootstrap 5 (BS5-15):
legal.html, legals.html, 403.html, 404.html and 500.html.

Run with `python manage.py test --tag browser` after one
`shoot --record --family legal`.

What reaches the API: nothing. The pages and the guest error pages replay
the legal family's recording (GETs only, as a guest). The signed-in refusals
(lane 9) answer a made-up huddle id, 99999150, with a made-up refusal in
replay mode only: no huddle id but the harness user's own is ever asked of
the API, because a real one could be someone's private messages. Sign out
on the Logged out page is caught in the browser and never reaches Django.
CS Grupetto (lane 10) is shot as a guest: a signed-in request to another
Site makes the harness user a profile there.
"""
from urllib.parse import parse_qs, urlsplit

from core import colors
from core.harness import manifest
from core.harness.admin_browser_tests import AdminTestCase
from core.harness.conversations_browser_tests import _fixture

LFGSS = manifest.LFGSS
LFGSS_API = 'https://lfgss.microcosm.app/api/v1'
CSGRUPETTO = 'csgrupetto.microcosm.app'
TERMS = '/about/terms/'
# A made-up huddle id: never asked of the API (see above).
STUB_HUDDLE = 99999150
# The status each legal family page answers with.
STATUS = {'error-404': 404, 'error-403': 403, 'error-500': 500}
# Pages whose query string the view passes on to the API: ?bs=5 would be a
# request the recording lacks, so they ask by the bs cookie only.
QUERY_TO_API = {'error-404', 'error-500'}


class LegalTestCase(AdminTestCase):
    """AdminTestCase brings assert_on_bs5 and the made-up answers (stub_setup, stub)."""

    def open_page(self, p, **kwargs):
        return self.open_bs5(p.path, host=p.host, signed_in=p.signed_in, status=STATUS.get(p.label, 200), **kwargs)


class Bs5LegalPagesTests(LegalTestCase):

    def test_every_legal_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('legal'):
            for by_cookie in (True,) if p.label in QUERY_TO_API else (False, True):
                with self.subTest(page=p.label, by_cookie=by_cookie):
                    page = self.open_page(p, by_cookie=by_cookie)
                    self.assert_on_bs5(page)
                    self.assertEqual(page.locator('main h1').count(), 1)
                    page.context.close()

    def test_nothing_overflows_on_phones_and_tablets(self):
        for p in manifest.pages_for('legal'):
            for width in (375, 768):
                with self.subTest(page=p.label, width=width):
                    page = self.open_page(p, width=width, by_cookie=p.label in QUERY_TO_API)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                    page.context.close()

    def test_about_links_each_policy(self):
        page = self.open_bs5('/about/')
        links = page.locator('main .mw-legal ul a')
        self.assertEqual([links.nth(i).get_attribute('href') for i in range(links.count())],
                         ['/about/terms/', '/about/privacy/', '/about/cookies/'])
        with page.expect_navigation(wait_until='load'):
            links.nth(1).click()
        self.assertEqual(urlsplit(page.url).path, '/about/privacy/')
        self.assert_on_bs5(page)
        self.assertEqual(page.locator('#mw-metabar .mw-module-heading').inner_text(), 'Privacy Policy')


# ---------------------------------------------------------------------------
# Lane 7: the terms' tables and lettered and roman lists.

LISTS_JS = """() => {
  const style = (s) => [...document.querySelectorAll(s)].map(e => getComputedStyle(e).listStyleType);
  const table = document.querySelector('main .mw-legal table');
  const cell = getComputedStyle(table.querySelector('td'));
  const head = getComputedStyle(table.querySelector('th'));
  const main = document.querySelector('main').getBoundingClientRect();
  const box = table.getBoundingClientRect();
  return {
    alpha: style('main ol[type=a]'), roman: style('main ol[type=i]'),
    tables: document.querySelectorAll('main .mw-legal table').length,
    font: getComputedStyle(document.querySelector('main .mw-legal p')).fontFamily,
    cellPadding: parseFloat(cell.paddingLeft), cellBorder: parseFloat(cell.borderTopWidth),
    cellAlign: cell.verticalAlign, headBorder: parseFloat(head.borderBottomWidth), headWeight: head.fontWeight,
    inside: box.left >= main.left && box.right <= main.right,
  };
}"""


class TermsTests(LegalTestCase):

    def test_tables_and_lettered_lists_read_well(self):
        for width in (1280, 375):
            with self.subTest(width=width):
                page = self.open_bs5(TERMS, width=width)
                facts = page.evaluate(LISTS_JS)
                self.assertGreater(len(facts['alpha']), 0)
                self.assertGreater(len(facts['roman']), 0)
                self.assertEqual(set(facts['alpha']), {'lower-alpha'})
                self.assertEqual(set(facts['roman']), {'lower-roman'})
                self.assertEqual(facts['tables'], 2)
                self.assertIn('Merriweather', facts['font'])
                self.assertEqual((facts['cellPadding'], facts['cellBorder'], facts['cellAlign']), (8, 1, 'top'))
                self.assertEqual(facts['headBorder'], 2)
                self.assertGreaterEqual(int(facts['headWeight']), 600)
                self.assertTrue(facts['inside'], 'the table stays inside the content column')
                if width == 1280:
                    page.locator('main ol[type=i]').first.scroll_into_view_if_needed()
                    self.snap(page, 'BS5-15-check-a')
                page.context.close()


# ---------------------------------------------------------------------------
# Lane 8: a missing address.

class NotFoundTests(LegalTestCase):

    def test_a_missing_address_is_not_found_on_bootstrap_5(self):
        page = self.open_bs5('/no-such-page/', status=404, by_cookie=True)
        self.assert_on_bs5(page)
        self.assertEqual(page.title(), 'Not Found | LFGSS')
        self.assertEqual(page.locator('main h1').inner_text(), 'Not Found')
        # The base around it: header, navigation, footer.
        self.assertTrue(page.locator('.mw-logo img').is_visible())
        self.assertTrue(page.locator('.mw-nav .navbar-nav').first.is_visible())
        self.assertTrue(page.locator('.mw-footer').is_visible())
        self.snap(page, 'BS5-15-check-b')
        with page.expect_navigation(wait_until='load'):
            page.get_by_role('link', name='Click here to go back to the homepage').click()
        self.assertEqual(urlsplit(page.url).path, '/')
        self.assert_on_bs5(page)

    def test_the_api_reason_for_a_server_error(self):
        page = self.open_bs5('/search/?q=bike', status=500, by_cookie=True)
        self.assertEqual(page.locator('main h1').inner_text(), 'Server Error')
        self.assertIn('The reason was:', page.locator('main').inner_text())
        self.assertFalse(page.get_by_text('CLOUDFLARE_ERROR_500S_BOX').is_visible())


# ---------------------------------------------------------------------------
# Lane 9: signed in, a huddle the harness user cannot see, made up.

class SignedInRefusalTests(LegalTestCase):

    def setUp(self):
        super().setUp()
        # Replay mode only, on the signed-in recording; catches anything sent.
        self.stub_setup()

    def refused(self, status, error):
        """The API's refusal of the made-up huddle, in its usual envelope."""
        return self.stub('refused-%d' % status,
                         [_fixture('GET %s/huddles/%d auth' % (LFGSS_API, STUB_HUDDLE), status, None, error)])

    def test_a_huddle_the_member_cannot_see(self):
        with self.refused(403, 'You do not have permission to view this huddle (made up)'):
            page = self.open_bs5('/huddles/%d/' % STUB_HUDDLE, signed_in=True, status=403)
        self.assert_on_bs5(page)
        self.assertEqual(page.locator('main h1').inner_text(), 'Not permitted')
        self.assertIn('This might happen if you\'re trying to view a private subforum.',
                      page.locator('main').inner_text())
        # The signed-in controls: the account box, Messages, the drawers' account links.
        account = page.locator('.mw-account')
        self.assertTrue(account.locator('#profile').is_visible())
        self.assertEqual(account.locator('#profile').get_attribute('href'),
                         '/profiles/%d/' % manifest.HARNESS_PROFILE_ID)
        self.assertTrue(account.get_by_role('link', name='Messages').is_visible())
        self.assertTrue(account.get_by_role('button', name='Sign out').is_visible())
        self.assertEqual(page.locator('#login').count(), 0)
        self.snap(page, 'BS5-15-signed-in')
        with page.expect_navigation(wait_until='load'):
            page.get_by_role('link', name='Click here to return to the home page').click()
        self.assertEqual(urlsplit(page.url).path, '/')
        self.assertEqual(self.api_writes, [])

    def test_an_expired_session(self):
        page = self.open_expired()
        self.assertEqual(page.title(), 'Logged out | LFGSS')
        self.assertEqual(page.locator('main h1').inner_text(), 'Logged out')
        self.snap(page, 'BS5-15-logged-out')
        # Sign out posts the base's form: caught here, it never reaches Django.
        posted = []

        def catch(route):
            posted.append((route.request.method, parse_qs(route.request.post_data or '')))
            route.fulfill(status=200, content_type='text/html', body='<!doctype html><title>signed out</title>')
        page.route('**/logout/', catch)
        with page.expect_navigation(wait_until='load'):
            page.get_by_role('button', name='view the site as a guest').click()
        self.assertEqual(len(posted), 1)
        self.assertEqual(posted[0][0], 'POST')
        self.assertIn('csrfmiddlewaretoken', posted[0][1])
        # Sign in again opens Lock.
        page = self.open_expired()
        page.get_by_role('button', name='sign in again to continue').click()
        page.locator('.auth0-lock input[type=email], .auth0-lock input[name=email]').first.wait_for(
            state='visible', timeout=15000)
        self.assertEqual(self.api_writes, [])

    def open_expired(self):
        with self.refused(401, 'Your session has expired (made up)'):
            return self.open_bs5('/huddles/%d/' % STUB_HUDDLE, signed_in=True, status=403)


# ---------------------------------------------------------------------------
# Lane 10: CS Grupetto's branding around its terms, as a guest.

COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    image: getComputedStyle(document.body).backgroundImage,
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    text: rgb(document.querySelector('main .mw-legal p'), 'color'),
    heading: rgb(document.querySelector('main .mw-legal h3'), 'color'),
    link: rgb(document.querySelector('main .mw-legal p a'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
  };
}"""


class CsGrupettoBrandingTests(LegalTestCase):

    def test_csgrupetto_terms_light_and_dark(self):
        site_link = colors.parse_hex('#00a6ed')
        surround = colors.parse_hex('#ffffff')
        for mode in ('light', 'dark'):
            with self.subTest(mode=mode):
                page = self.open_bs5(TERMS, host=CSGRUPETTO, color_mode=mode)
                facts = page.evaluate(COLOR_FACTS_JS)
                self.assertEqual(facts['theme'], mode)
                self.assertEqual(tuple(facts['surround']), surround, 'the Site surround')
                self.assertIn('url(', facts['image'], 'the Site background image')
                self.assertEqual(facts['logo'], 89)
                self.assertGreaterEqual(colors.contrast(facts['text'], facts['main']), 7)
                self.assertGreaterEqual(colors.contrast(facts['heading'], facts['main']), colors.AA)
                if mode == 'light':
                    self.assertEqual(tuple(facts['link']), site_link)
                else:
                    self.assertGreaterEqual(colors.contrast(facts['link'], facts['main']), colors.AA)
                self.snap(page, 'BS5-15-branding-%s' % mode)
                page.context.close()
