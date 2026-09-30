"""Interaction checks for the profiles family on Bootstrap 5 (BS5-09).

Run with `python manage.py test --tag browser` after one `shoot --record`
(with HARNESS_TOKEN set, for the signed-in pages). Every page is asked for
with ?bs=5, so it renders from core/templates_bs5/.

What reaches the API:
- Nothing, from the filters, avatar, Follow and Ignore checks. The avatar
  preview never submits the profile form, and never may: the harness user is
  the operator's real account.
- SettingsWriteTests changes one of the harness user's notification settings
  and then puts it back, the one write the operator allowed. It is recorded
  once into fixtures/update-settings/ with

      HARNESS_MODE=record HARNESS_WRITE_SETTINGS=54446 python manage.py test \\
          --tag browser core.harness.profiles_browser_tests.SettingsWriteTests

  and replayed from then on. The check fails unless every setting reads back
  as it was before.
"""
import os
import struct
import zlib
from urllib.parse import parse_qs, urlsplit

from django.test import override_settings

from core import colors
from core.harness import manifest, recorder
from core.harness.browser_tests import BrowserTestCase
from core.harness.lists_browser_tests import OverlayRecording

LFGSS = manifest.LFGSS
CSGRUPETTO = 'csgrupetto.microcosm.app'
PEOPLE = '/profiles/?top=true'
OTHER_PROFILE = '/profiles/47714/'
OWN_PROFILE = '/profiles/%d/' % manifest.HARNESS_PROFILE_ID
EDIT_PROFILE = '/profiles/%d/edit/' % manifest.HARNESS_PROFILE_ID
SETTINGS = '/updates/settings/'
PEOPLE_ROWS = 'ul.mw-people > li'

def png(size=8):
    """A small orange PNG, for the avatar preview."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = b''.join(b'\x00' + b'\xf0\x80\x30' * size for _ in range(size))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


PNG = png()


class ProfilesTestCase(BrowserTestCase):
    """Family pages open with BrowserTestCase.open_bs5."""

    def assert_on_bs5(self, page):
        self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'), 'not the Bootstrap 5 base')

    def no_posts(self, page):
        """Every POST the page sends from now on; a check asserts it stays empty."""
        posts = []
        page.on('request', lambda r: posts.append(r.url) if r.method == 'POST' else None)
        return posts


class Bs5ProfilePagesTests(ProfilesTestCase):

    def test_every_profiles_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('profiles'):
            with self.subTest(page=p.label):
                page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in)
                self.assert_on_bs5(page)
                self.assertTrue(page.locator('main h1').first.is_visible())
                page.context.close()

    def test_nothing_overflows_on_phones_and_tablets(self):
        for p in manifest.pages_for('profiles'):
            for width in (375, 768):
                with self.subTest(page=p.label, width=width):
                    page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in, width=width)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                    page.context.close()


class FiltersTests(ProfilesTestCase):
    """Lane 7: filter the people list by Online now."""

    def test_online_now_filters_the_list_and_the_url_carries_it(self):
        page = self.open_bs5(PEOPLE)
        before = [a.get_attribute('href') for a in page.locator(PEOPLE_ROWS + ' .mw-person-link').all()]
        self.assertEqual(len(before), 25)
        with page.expect_navigation(wait_until='load'):
            page.get_by_label('Online now').check()
        url = urlsplit(page.url)
        self.assertEqual(url.path, '/profiles/')
        self.assertEqual(url.query, 'online=true&top=true')
        self.assert_on_bs5(page)
        self.assertTrue(page.get_by_label('Online now').is_checked())
        self.assertTrue(page.get_by_label('Order by comment count').is_checked())
        self.assertIn('online now, most comments', page.locator('main').inner_text())
        after = [a.get_attribute('href') for a in page.locator(PEOPLE_ROWS + ' .mw-person-link').all()]
        self.assertTrue(after, 'nobody online in the recording')
        self.assertNotEqual(after, before, 'the list did not change')
        self.snap(page, 'BS5-09-check-a')

    def test_name_and_unticking_keep_the_other_filters(self):
        page = self.open_bs5(PEOPLE)
        asked = []

        # Answered here: these lists are not in the recording.
        def answer(route):
            asked.append(route.request.url)
            route.fulfill(status=200, content_type='text/html', body='<p>filtered</p>')

        page.route(lambda url: urlsplit(url).path == '/profiles/', answer)
        with page.expect_navigation():
            page.get_by_label('Name starting with').select_option('d')
        self.assertEqual(parse_qs(urlsplit(asked[-1]).query), {'q': ['d'], 'top': ['true']})

        page = self.open_bs5(PEOPLE)
        page.route(lambda url: urlsplit(url).path == '/profiles/', answer)
        with page.expect_navigation():
            page.get_by_label('Order by comment count').click()  # unticks it, and the page goes
        self.assertEqual(urlsplit(asked[-1]).query, '')


class AvatarTests(ProfilesTestCase):
    """Lane 8: a new avatar shows in the box before the form is saved. Nothing is
    submitted: the profile belongs to the operator's real account."""

    def preview_facts(self, page):
        return page.locator('[data-mw-avatar-drop]').evaluate('''drop => {
          const img = drop.querySelector('img');
          return { src: img.getAttribute('src') || '', hidden: img.hidden,
                   hasImage: drop.classList.contains('has-image'), files: drop.querySelector('input').files.length };
        }''')

    def test_choosing_an_image_previews_it_before_save(self):
        page = self.open_bs5(EDIT_PROFILE, signed_in=True)
        posts = self.no_posts(page)
        start = self.preview_facts(page)
        self.assertEqual(start['files'], 0)
        page.locator('#avatar').set_input_files([{'name': 'me.png', 'mimeType': 'image/png', 'buffer': PNG}])
        page.wait_for_function('() => document.querySelector("[data-mw-avatar-drop] img").naturalWidth > 0')
        facts = self.preview_facts(page)
        self.assertTrue(facts['src'].startswith('blob:'), facts['src'])
        self.assertFalse(facts['hidden'])
        self.assertTrue(facts['hasImage'])
        self.assertEqual(facts['files'], 1)
        self.assertFalse(page.locator('[data-mw-avatar-drop] span').is_visible(), '"Click here" stays over the image')
        self.snap(page, 'BS5-09-check-b')

        # A file that is not an image is refused; the box goes back to how it loaded.
        page.locator('#avatar').set_input_files([{'name': 'notes.txt', 'mimeType': 'text/plain', 'buffer': b'x'}])
        facts = self.preview_facts(page)
        self.assertEqual((facts['src'], facts['hidden'], facts['hasImage'], facts['files']),
                         (start['src'], start['hidden'], start['hasImage'], 0))

        # Cancel resets the form and the box.
        page.locator('#avatar').set_input_files([{'name': 'me.png', 'mimeType': 'image/png', 'buffer': PNG}])
        page.get_by_role('button', name='Cancel').click()
        page.wait_for_function('(src) => (document.querySelector("[data-mw-avatar-drop] img").getAttribute("src") || "") === src',
                               arg=start['src'])
        self.assertEqual(self.preview_facts(page)['files'], 0)
        self.assertEqual(posts, [])

    def test_dropping_an_image_previews_it(self):
        page = self.open_bs5(EDIT_PROFILE, signed_in=True)
        posts = self.no_posts(page)
        page.locator('[data-mw-avatar-drop]').evaluate('''(drop, bytes) => {
          const data = new DataTransfer();
          data.items.add(new File([new Uint8Array(bytes)], 'dropped.png', { type: 'image/png' }));
          drop.dispatchEvent(new DragEvent('dragover', { dataTransfer: data, bubbles: true, cancelable: true }));
          drop.dispatchEvent(new DragEvent('drop', { dataTransfer: data, bubbles: true, cancelable: true }));
        }''', list(PNG))
        page.wait_for_function('() => document.querySelector("[data-mw-avatar-drop] img").naturalWidth > 0')
        facts = self.preview_facts(page)
        self.assertTrue(facts['src'].startswith('blob:'))
        self.assertEqual(facts['files'], 1, 'the dropped file is the one the form would send')
        self.assertEqual(page.locator('#avatar').evaluate('el => el.files[0].name'), 'dropped.png')
        self.assertEqual(posts, [])

    def test_the_name_is_checked_before_sending(self):
        page = self.open_bs5(EDIT_PROFILE, signed_in=True)
        posts = self.no_posts(page)
        name = page.get_by_label('Choose a username by which you wish to be known')
        self.assertEqual(name.input_value(), 'duncs')
        for bad in ('', 'two words', 'a@b', 'x'):
            with self.subTest(name=bad):
                name.fill(bad)
                page.get_by_role('button', name='Save Changes').click()
                self.assertIn('is-invalid', name.get_attribute('class'))
                self.assertTrue(name.evaluate('el => el === document.activeElement'))
        page.wait_for_timeout(200)
        self.assertEqual(posts, [])


class SignedInControlsTests(ProfilesTestCase):
    """Lane 9: the signed-in controls on profiles and the settings form."""

    def test_someone_elses_profile(self):
        page = self.open_bs5(OTHER_PROFILE, signed_in=True)
        self.assertEqual(page.get_by_role('link', name='Send Message').get_attribute('href'), '/huddles/create/?to=47714')
        self.assertEqual(page.locator('#ignore_form').get_attribute('action'), '/ignore/')
        self.assertTrue(page.get_by_role('button', name='Ignore').is_visible())

        # Follow, answered here: nothing reaches the API.
        posts = []

        def answer(route):
            posts.append(parse_qs(route.request.post_data))
            route.fulfill(status=200, body='')

        page.route('**/watchers/', answer)
        control = page.locator('[data-mw-subscribe]')
        control.get_by_role('button', name='Follow @').click()
        page.wait_for_function('document.querySelector("[data-mw-subscribe]").dataset.state === "on"')
        self.assertEqual({k: posts[0][k] for k in ('itemId', 'itemType', 'updateTypeId')},
                         {'itemId': ['47714'], 'itemType': ['profile'], 'updateTypeId': ['1']})
        self.snap(page, 'profiles-follow')

    def test_own_profile(self):
        page = self.open_bs5(OWN_PROFILE, signed_in=True)
        metabar = page.locator('#mw-metabar')
        self.assertEqual(metabar.get_by_role('link', name='Edit your Profile').get_attribute('href'), EDIT_PROFILE)
        self.assertEqual(metabar.get_by_role('link', name='View Ignored').get_attribute('href'), '/ignored/')
        self.assertEqual(page.locator('[data-mw-subscribe]').count(), 0)

    def test_follow_the_people_page(self):
        page = self.open_bs5(PEOPLE, signed_in=True)
        control = page.locator('[data-mw-subscribe]')
        self.assertEqual((control.get_attribute('data-item-type'), control.get_attribute('data-item-id'),
                          control.get_attribute('data-update-type')), ('profile', '0', '9'))
        self.assertTrue(page.locator(PEOPLE_ROWS + ' .mw-person-message').first.is_visible())

    def test_guest_send_message_opens_the_signin_modal(self):
        page = self.open_bs5(OTHER_PROFILE)
        page.locator('#mw-metabar').get_by_role('button', name='Send Message').click()
        page.locator('#modal-signin.show').wait_for()

    def test_the_global_switch_turns_the_group_off_and_on(self):
        page = self.open_bs5(SETTINGS, signed_in=True)
        posts = self.no_posts(page)
        master = page.get_by_label('Enable notifications')
        boxes = page.locator('input[name^=send_email_]')
        start = boxes.evaluate_all('els => els.map(e => e.checked)')
        self.assertEqual(len(start), 9)
        master.uncheck()
        self.assertEqual(boxes.evaluate_all('els => els.map(e => [e.checked, e.disabled])'), [[False, True]] * 9)
        master.check()
        self.assertEqual(boxes.evaluate_all('els => els.map(e => [e.checked, e.disabled])'), [[True, False]] * 9)
        page.get_by_role('button', name='Cancel').click()
        self.assertEqual(boxes.evaluate_all('els => els.map(e => e.checked)'), start)
        self.assertTrue(master.is_checked())
        # Each description is its switch's label.
        self.assertEqual(page.get_by_label('When a comment of yours is replied to').get_attribute('name'), 'send_email_2')
        self.assertEqual(posts, [])


# The harness forwards https pages to an http server with X-Forwarded-Proto;
# trusting it lets a real form POST pass Django's CSRF origin check.
@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class SettingsWriteTests(ProfilesTestCase):
    """Lane 9, live once: change one notification setting, save, then put it
    back and save again. Every step replays from fixtures/update-settings/."""

    TOGGLED = 'send_email_1'

    def setUp(self):
        self.recording = os.path.join(self.fixtures_dir, 'update-settings')
        if self._recorder.mode == recorder.REPLAY:
            if not os.path.isdir(self.recording):
                self.skipTest('No notification settings recording in %s. Record it once: HARNESS_MODE=record '
                              'HARNESS_WRITE_SETTINGS=%d python manage.py test --tag browser '
                              'core.harness.profiles_browser_tests.SettingsWriteTests'
                              % (self.recording, manifest.HARNESS_PROFILE_ID))
        elif os.environ.get('HARNESS_WRITE_SETTINGS') != str(manifest.HARNESS_PROFILE_ID):
            self.skipTest('Recording changes the live settings of profile %d; set HARNESS_WRITE_SETTINGS=%d to allow it.'
                          % (manifest.HARNESS_PROFILE_ID, manifest.HARNESS_PROFILE_ID))

    def step(self, name):
        return OverlayRecording(self._recorder, self.fixtures_dir, os.path.join('update-settings', name))

    def settings(self, page):
        return page.evaluate('''() => Object.fromEntries([...document.querySelectorAll(
          "form[data-mw-settings] input[type=checkbox]")].map(e => [e.name, e.checked]))''')

    def save(self, page):
        self.submit(page, page.get_by_role('button', name='Save Changes').click, SETTINGS)
        self.assertEqual(urlsplit(page.url).path, SETTINGS)
        self.assert_on_bs5(page)

    def test_change_a_setting_and_put_it_back(self):
        page = self.new_page(signed_in=True)
        page.context.add_cookies([{'name': 'bs', 'value': '5', 'url': 'https://%s/' % LFGSS}])
        sent = []
        page.on('request', lambda r: sent.append((r.url, r.post_data)) if r.method == 'POST' else None)

        with self.step('0-before'):
            page.goto('https://%s%s' % (LFGSS, SETTINGS), wait_until='load')
            self.assert_on_bs5(page)
            original = self.settings(page)
            self.assertEqual(len(original), 10)

        with self.step('1-changed'):
            page.locator('#' + self.TOGGLED).set_checked(not original[self.TOGGLED])
            self.save(page)
            self.assertEqual(urlsplit(sent[-1][0]).path, SETTINGS)
            changed = self.settings(page)
            self.assertEqual(changed, dict(original, **{self.TOGGLED: not original[self.TOGGLED]}))
            self.snap(page, 'BS5-09-signed-in')

        with self.step('2-restored'):
            page.locator('#' + self.TOGGLED).set_checked(original[self.TOGGLED])
            self.save(page)
            self.assertEqual(self.settings(page), original)

        # A fresh load, not the page the redirect landed on.
        with self.step('3-verified'):
            page.goto('https://%s%s' % (LFGSS, SETTINGS), wait_until='load')
            self.assertEqual(self.settings(page), original, 'the settings were not put back')
        self.assertEqual(len(sent), 2)


# Colour facts on the people list: the surround, the content and its links.
COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    image: getComputedStyle(document.body).backgroundImage,
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    link: rgb(document.querySelector('.mw-list-title a'), 'color'),
    person: rgb(document.querySelector('.mw-person-link strong'), 'color'),
    footerLink: rgb(document.querySelector('.mw-footer a'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
  };
}"""


class CsGrupettoBrandingTests(ProfilesTestCase):
    """Lane 10: Site branding holds on the people list in light and dark."""

    def test_csgrupetto_people_light_and_dark(self):
        site_link = colors.parse_hex('#00a6ed')
        surround = colors.parse_hex('#ffffff')
        for mode in ('light', 'dark'):
            with self.subTest(mode=mode):
                page = self.open_bs5(PEOPLE, host=CSGRUPETTO, color_mode=mode)
                facts = page.evaluate(COLOR_FACTS_JS)
                self.assertEqual(facts['theme'], mode)
                self.assertEqual(tuple(facts['surround']), surround, 'the Site surround')
                self.assertIn('url(', facts['image'], 'the Site background image')
                self.assertEqual(facts['logo'], 89)
                self.assertGreaterEqual(colors.contrast(facts['person'], facts['main']), 7)
                if mode == 'light':
                    self.assertEqual(tuple(facts['link']), site_link)
                    self.assertEqual(tuple(facts['footerLink']), site_link)
                else:
                    self.assertGreaterEqual(colors.contrast(facts['link'], facts['main']), colors.AA)
                    self.assertGreaterEqual(colors.contrast(facts['footerLink'], colors.dark_panel(surround)), colors.AA)
                self.snap(page, 'BS5-09-branding-%s' % mode)
                page.context.close()
