"""Interaction checks for the forum lists family on Bootstrap 5 (BS5-07).

Run with `python manage.py test --tag browser` after one `shoot --record`
(with HARNESS_TOKEN set, for the signed-in pages). Every page is asked for
with ?bs=5, so it renders from core/templates_bs5/.

Mark everything read is the one check that changes the harness user's real
account: it marks lfgss Social (manifest.HARNESS_MARK_READ_MICROCOSM_ID) read.
Its after-state lives in its own recording, fixtures/mark-read/, made once
with

    HARNESS_MODE=record python manage.py test --tag browser \\
        core.harness.lists_browser_tests.MarkReadTests

and replayed from then on. Everything else writes nothing: Follow and the
forum search are answered in the browser.
"""
import os
from urllib.parse import parse_qs, urlsplit

from django.test import override_settings

from core import colors
from core.harness import manifest, recorder
from core.harness.browser_tests import BrowserTestCase

LFGSS = manifest.LFGSS
ESPRUINO = 'forum.espruino.com'
FORUM = '/microcosms/509/'
MARK_READ_FORUM = '/microcosms/%d/' % manifest.HARNESS_MARK_READ_MICROCOSM_ID
NEW_BADGES = 'ul.mw-rows .badge.text-bg-warning'


class ListsTestCase(BrowserTestCase):
    """Lists pages open with BrowserTestCase.open_bs5; this checks they are Bootstrap 5 lists."""

    def assert_on_bs5(self, page):
        self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'), 'not the Bootstrap 5 base')
        self.assertGreater(page.locator('ul.mw-rows > li').count(), 0, 'no Bootstrap 5 list rows')


class Bs5ListPagesTests(ListsTestCase):

    def test_every_lists_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('lists'):
            with self.subTest(page=p.label):
                page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in)
                self.assert_on_bs5(page)
                page.context.close()


class PageJumpTests(ListsTestCase):

    def test_typing_a_page_and_pressing_enter_jumps_there(self):
        page = self.open_bs5(FORUM)
        self.assert_on_bs5(page)
        form = page.locator('.mw-list-header form[name=paginationByOffset]')
        self.assertEqual(form.get_attribute('data-limit'), '25')
        field = form.locator('input[inputmode=numeric]')
        field.fill('3')
        with page.expect_navigation(wait_until='load'):
            field.press('Enter')
        url = urlsplit(page.url)
        self.assertEqual(url.path, FORUM)
        self.assertEqual(parse_qs(url.query).get('offset'), ['50'])
        self.assert_on_bs5(page)
        self.assertEqual(page.locator('.mw-list-header .page-item.active').inner_text().strip(), '3')
        self.assertEqual(page.locator('.mw-list-header .mw-page-jump input[inputmode=numeric]').input_value(), '3')
        self.snap(page, 'lists-page-jump')

    def test_the_current_page_or_nonsense_does_not_navigate(self):
        page = self.open_bs5(FORUM)
        field = page.locator('.mw-list-header .mw-page-jump input[inputmode=numeric]')
        for value in ('1', 'x', '0', '100000'):
            with self.subTest(value=value):
                field.fill(value)
                field.press('Enter')
                page.wait_for_timeout(200)
                self.assertEqual(urlsplit(page.url).path, FORUM)
                self.assertNotIn('offset', page.url)


class OverlayRecording(object):
    """From now on, replay API calls from fixtures/<name>/ before the main
    recording; in record mode, fetch them afresh into it. The live server runs
    in this process, so swapping the recorder's folder here reaches it."""

    def __init__(self, rec, fixtures_dir, name):
        self.rec = rec
        self.name = name
        self.dir = os.path.join(fixtures_dir, name, 'api')
        self.base_dir = rec.dir

    def __enter__(self):
        self.saved = (self.rec.dir, self.rec.session)
        self.rec.dir = self.dir
        # A new session makes record mode fetch every key again.
        self.rec.session = '%s/%s' % (self.rec.session, self.name)
        if self.rec.mode == recorder.REPLAY:
            overlay_load = self.rec.load

            # The live server loads keys from several threads at once, so the
            # fallback reads the main recording's folder, never switching rec.dir.
            def load(key):
                found = overlay_load(key)
                return found if found is not None else recorder.load_from(self.base_dir, key)
            self.rec.load = load
        return self

    def __exit__(self, *exc):
        self.rec.dir, self.rec.session = self.saved
        self.rec.__dict__.pop('load', None)


# The harness forwards https pages to an http server with X-Forwarded-Proto;
# trusting it lets a real form POST pass Django's CSRF origin check.
@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class MarkReadTests(ListsTestCase):

    def test_mark_everything_read_clears_the_new_badges(self):
        overlay = OverlayRecording(self._recorder, self.fixtures_dir, 'mark-read')
        if self._recorder.mode == recorder.REPLAY and not os.path.isdir(overlay.dir):
            self.skipTest('No Mark everything read recording in %s. Record it once (it marks lfgss Social read '
                          'for the harness user): HARNESS_MODE=record python manage.py test --tag browser '
                          'core.harness.lists_browser_tests.MarkReadTests' % overlay.dir)
        page = self.open_bs5(MARK_READ_FORUM, signed_in=True)
        before = page.locator(NEW_BADGES).count()
        self.assertGreater(before, 0, 'the recording has no NEW badges to clear')
        self.snap(page, 'lists-mark-read-before')

        form = page.locator('#mark-read-module')
        self.assertEqual(form.locator('input[name=item_type]').input_value(), 'microcosm')
        self.assertEqual(form.locator('input[name=item_id]').input_value(),
                         str(manifest.HARNESS_MARK_READ_MICROCOSM_ID))
        with overlay:
            self.submit(page, form.get_by_role('button', name='Mark everything read').click,
                        form.get_attribute('action'))
            self.assertEqual(urlsplit(page.url).path, MARK_READ_FORUM)
            page.reload(wait_until='load')
            self.assert_on_bs5(page)
            self.assertEqual(page.locator(NEW_BADGES).count(), 0, 'NEW badges left after Mark everything read')
            self.snap(page, 'lists-mark-read-after')


class SignedInControlsTests(ListsTestCase):

    def test_home_signed_in(self):
        page = self.open_bs5('/', signed_in=True)
        self.assert_on_bs5(page)
        self.assertTrue(page.locator('.mw-account #profile').is_visible())
        actions = page.locator('.mw-module', has=page.get_by_role('heading', name='Actions'))
        button = actions.get_by_role('button', name='Mark everything read')
        self.assertTrue(button.is_visible())
        self.assertEqual(actions.locator('form').get_attribute('action'), '/profiles/read/')
        self.assertEqual(actions.locator('input[name=return_path]').input_value(), '/?bs=5')
        # Rows link signed-in members to the newest comment.
        self.assertRegex(page.locator('ul.mw-rows .mw-row-recent a').first.get_attribute('href'),
                         r'^/(conversations|events)/\d+/newest/$')
        self.snap(page, 'lists-signed-in')

    def test_forum_signed_in(self):
        page = self.open_bs5(MARK_READ_FORUM, signed_in=True)
        forum = str(manifest.HARNESS_MARK_READ_MICROCOSM_ID)
        self.assertEqual(page.locator('#create_conversation').get_attribute('href'),
                         '/microcosms/%s/create/conversation/' % forum)
        self.assertEqual(page.locator('#create_event').get_attribute('href'), '/microcosms/%s/create/event/' % forum)
        self.assertTrue(page.get_by_role('button', name='Ignore').is_visible())
        self.assertEqual(page.locator('#ignore_form').get_attribute('action'), '/ignore/')

        # Follow, answered here: nothing reaches the API.
        posts = []

        def answer(route):
            posts.append(parse_qs(route.request.post_data))
            route.fulfill(status=200, body='')

        page.route('**/watchers/', answer)
        control = page.locator('[data-mw-subscribe]')
        self.assertEqual(control.get_attribute('data-state'), 'off')
        self.assertFalse(control.locator('input[name=emailme]').is_visible())
        control.get_by_role('button', name='Follow').click()
        page.wait_for_function('document.querySelector("[data-mw-subscribe]").dataset.state === "on"')
        self.assertTrue(control.get_by_text('Following').is_visible())
        self.assertTrue(control.locator('input[name=emailme]').is_visible())
        self.snap(page, 'lists-follow')
        control.get_by_role('button', name='unfollow').click()
        page.wait_for_function('document.querySelector("[data-mw-subscribe]").dataset.state === "off"')
        self.assertEqual(len(posts), 2)
        self.assertEqual({k: posts[0][k] for k in ('itemId', 'itemType', 'updateTypeId')},
                         {'itemId': [forum], 'itemType': ['microcosm'], 'updateTypeId': ['8']})
        self.assertEqual(posts[1]['delete'], ['true'])

        # Search this forum, answered here too.
        searched = []

        def search(route):
            searched.append(route.request.url)
            route.fulfill(status=200, content_type='text/html', body='<p>results</p>')

        page.route('**/search/**', search)
        field = page.get_by_role('searchbox', name='Search this forum')
        field.fill('beers')
        with page.expect_navigation():
            field.press('Enter')
        query = parse_qs(urlsplit(searched[0]).query)
        self.assertEqual((query['q'], query['forumId'], query['defaults']), (['beers'], [forum], ['true']))

    def test_guest_post_buttons_open_the_signin_modal(self):
        page = self.open_bs5(FORUM)
        page.get_by_role('button', name='Post a conversation').click()
        page.locator('#modal-signin.show').wait_for()
        self.snap(page, 'lists-guest-post')


# Colour facts on a list page: the surround, the content and a link in a row.
COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  const body = getComputedStyle(document.body);
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    image: body.backgroundImage,
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    link: rgb(document.querySelector('ul.mw-rows .mw-row-recent a'), 'color'),
    metabarLink: rgb(document.querySelector('#mw-metabar .mw-counts a'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
  };
}"""


class EspruinoBrandingTests(ListsTestCase):
    """Site branding holds on the family's main page in light and dark."""

    def test_espruino_home_light_and_dark(self):
        site_link = colors.parse_hex('#4898AC')
        for mode in ('light', 'dark'):
            with self.subTest(mode=mode):
                page = self.open_bs5('/', host=ESPRUINO, color_mode=mode)
                facts = page.evaluate(COLOR_FACTS_JS)
                self.assertEqual(facts['theme'], mode)
                self.assertIn('url(', facts['image'], 'the Site background image')
                self.assertEqual(facts['logo'], 89)
                if mode == 'light':
                    light_surround = facts['surround']
                    self.assertEqual(tuple(facts['link']), site_link)
                else:
                    self.assertEqual(facts['surround'], light_surround, 'the surround changed with the Color mode')
                    metabar = colors.dark_panel(tuple(facts['surround']))
                    for name in ('link', 'metabarLink'):
                        self.assertGreaterEqual(colors.contrast(facts[name], facts['main']), colors.AA, name)
                        self.assertGreaterEqual(colors.contrast(facts[name], metabar), colors.AA, name)
                self.snap(page, 'lists-espruino-%s' % mode)
                page.context.close()
