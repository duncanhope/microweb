"""Interaction checks for the events family on Bootstrap 5 (BS5-11): the event
page, its header and map, the attendees modal and RSVP.

Run with `python manage.py test --tag browser` after one `shoot --record`
(with HARNESS_TOKEN set, for the signed-in pages). Every page is asked for
with ?bs=5, so it renders from core/templates_bs5/.

What reaches the API: nothing is written.
- RSVP (RsvpTests) is answered from a recording this module makes up from the
  base recording of manifest.RSVP_EVENT_ID, so it runs in replay mode only:
  the operator decided that no live RSVP is made. A real RSVP is a manual
  check for the operator before BS5-16.
- The map check pans Google's road map. Its images are browser GETs, recorded
  once into the HAR with

      HARNESS_MODE=record python manage.py test --tag browser \\
          core.harness.events_browser_tests.EventMapTests

  and replayed from then on. That class only reads.
"""
import copy
import json
import os
import shutil
import tempfile
from datetime import timedelta
from urllib.parse import urlsplit

from django.test import override_settings

from core import colors
from core.harness import manifest, recorder
from core.harness.browser_tests import BrowserTestCase
from core.harness.conversations_browser_tests import _fixture, _write
from core.harness.lists_browser_tests import OverlayRecording

LFGSS = manifest.LFGSS
ESPRUINO = 'forum.espruino.com'
EVENT = '/events/4488/'
LFGSS_API = 'https://lfgss.microcosm.app/api/v1'
MODAL = '#modal-event-attendees'


class EventsTestCase(BrowserTestCase):

    def assert_on_bs5(self, page):
        self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'), 'not the Bootstrap 5 base')


class Bs5EventPagesTests(EventsTestCase):

    def test_every_events_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('events'):
            with self.subTest(page=p.label):
                page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in)
                self.assert_on_bs5(page)
                self.assertTrue(page.locator('main h1').first.is_visible())
                if p.path.startswith('/events/'):
                    self.assertTrue(page.locator('.mw-event').is_visible())
                page.context.close()

    def test_nothing_overflows_on_phones_and_tablets(self):
        for p in manifest.pages_for('events'):
            for width in (375, 768):
                with self.subTest(page=p.label, width=width):
                    page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in, width=width)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                    page.context.close()


class AttendeesModalTests(EventsTestCase):
    """Lane 7: Going and Invited open everyone going; focus stays in the
    modal, and Escape closes it."""

    def in_modal(self, page):
        return page.evaluate('(s) => !!document.activeElement.closest(s)', MODAL)

    def test_counts_open_the_modal_which_traps_focus_and_closes_on_escape(self):
        page = self.open_bs5(EVENT)
        counts = page.locator('.mw-event-counts')
        self.assertEqual(counts.inner_text().split(), ['Going', '21', 'Invited', '5'])
        counts.click()
        modal = page.locator(MODAL + '.show')
        modal.wait_for()
        self.assertEqual(page.locator(MODAL).get_attribute('aria-modal'), 'true')
        self.assertEqual(modal.get_by_role('heading', level=2).inner_text(), 'The IKEA ride')
        # The view asks the API for one page of attendees, 25 of the 26 (as on
        # Bootstrap 3); Going is the API's own count.
        self.assertEqual(modal.locator('.mw-attendees li').count(), 25)
        self.assertEqual(modal.locator('.mw-attendees li em').count(), 5, 'five invited')
        self.assertTrue(self.in_modal(page), 'focus did not move into the modal')
        self.snap(page, 'BS5-11-check-a')

        # Tab and Shift+Tab never leave it: it has one link per person and two buttons.
        for key in ['Tab'] * 30 + ['Shift+Tab'] * 5:
            page.keyboard.press(key)
            self.assertTrue(self.in_modal(page), 'focus left the modal after %s' % key)
        page.keyboard.press('Escape')
        page.locator(MODAL).wait_for(state='hidden')
        self.assertTrue(counts.evaluate('el => el === document.activeElement'), 'focus did not return to Going')

    def test_more_button_and_close(self):
        page = self.open_bs5(EVENT, width=375)
        more = page.locator('.mw-event-people').get_by_role('button', name='Everyone going and invited')
        self.assertEqual(more.inner_text(), '+16')
        more.click()
        page.locator(MODAL + '.show').wait_for()
        page.locator(MODAL + ' .modal-footer').get_by_role('button', name='Close').click()
        page.locator(MODAL).wait_for(state='hidden')

    def test_attendee_tooltips(self):
        page = self.open_bs5(EVENT)
        avatar = page.locator('.mw-event-people a').first
        avatar.hover()
        page.locator('.tooltip.show').wait_for()
        self.assertEqual(page.locator('.tooltip.show').inner_text(), avatar.get_attribute('data-bs-original-title'))


MAP_FACTS_JS = """() => {
  const el = document.querySelector('[data-mw-event-map]');
  const c = el.mwMap.getCenter();
  const layer = el.querySelector('.leaflet-google-layer');
  return {
    center: [c.lat, c.lng],
    zoom: el.mwMap.getZoom(),
    scheme: getComputedStyle(el).colorScheme,
    zoomBg: getComputedStyle(el.querySelector('.leaflet-bar a')).backgroundColor,
    marker: el.querySelector('img.leaflet-marker-icon').naturalWidth,
    imagery: layer ? [...layer.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth > 0).length : 0,
  };
}"""


class EventMapTests(EventsTestCase):
    """Lane 8: the map draws, pans, and keeps Leaflet's light UI in dark mode."""

    def open_map(self, **kwargs):
        page = self.open_bs5(EVENT, **kwargs)
        page.wait_for_function('() => document.querySelector("[data-mw-event-map]").mwMap')
        page.wait_for_load_state('networkidle')
        return page

    def test_pan_the_map(self):
        page = self.open_map()
        before = page.evaluate(MAP_FACTS_JS)
        self.assertGreater(before['marker'], 0, 'no marker')
        self.assertGreater(before['imagery'], 0, 'Google drew no map')
        box = page.locator('[data-mw-event-map]').bounding_box()
        x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x - 150, y - 80, steps=10)
        page.mouse.up()
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(500)
        after = page.evaluate(MAP_FACTS_JS)
        self.assertNotEqual(after['center'], before['center'], 'the map did not pan')
        self.assertEqual(after['zoom'], before['zoom'])
        # Google moves its first picture with the pan but draws no more of it,
        # on Bootstrap 3 too (a Google Maps API problem, reported in BS5-11).
        self.assertGreater(after['imagery'], 0, 'Google drew nothing after the pan')

        # The other layers are Leaflet's own tiles.
        page.locator('.leaflet-control-layers').hover()
        page.get_by_label('Open Cycle Map').check()
        page.wait_for_function('() => [...document.querySelectorAll("img.leaflet-tile-loaded")]'
                               '.some(i => i.naturalWidth > 0)', timeout=10000)
        self.assertEqual(page.locator('.leaflet-google-layer').count(), 0)
        page.mouse.move(x, y)
        self.snap(page, 'BS5-11-check-b')

    def test_map_stays_light_in_dark_mode(self):
        page = self.open_map(color_mode='dark')
        self.assertEqual(page.evaluate('document.documentElement.dataset.bsTheme'), 'dark')
        facts = page.evaluate(MAP_FACTS_JS)
        self.assertEqual(facts['scheme'], 'light')
        self.assertEqual(facts['zoomBg'], 'rgb(255, 255, 255)')
        self.assertGreater(facts['imagery'], 0)
        self.snap(page, 'BS5-11-check-b-dark')

    def test_later_pages_have_no_map(self):
        page = self.open_bs5(EVENT + '?offset=25')
        self.assertEqual(page.locator('[data-mw-event-map]').count(), 0)
        self.assertEqual(page.locator('script[src*="leaflet"], link[href*="leaflet"]').count(), 0)
        self.assertEqual(page.locator('.mw-event-fact').count(), 3)


# ---------------------------------------------------------------------------
# Lane 9: RSVP, answered from a made-up recording.

# The harness forwards https pages to an http server with X-Forwarded-Proto;
# trusting it lets the RSVP form's POST pass Django's CSRF origin check.
@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class RsvpTests(EventsTestCase):
    """RSVP yes, then "Can't make it", on the test event moved into the
    future. Every API answer is made up from the base recording; the API's
    PUT is caught here and never leaves the process."""

    EVENT_ID = manifest.RSVP_EVENT_ID

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stub_fixtures = tempfile.mkdtemp(prefix='bs5-11-rsvp-')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.stub_fixtures, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        if self._recorder.mode != recorder.REPLAY:
            self.skipTest('The made-up RSVP recording runs in replay mode only: it must never reach the API.')
        self.event_url = '%s/events/%d' % (LFGSS_API, self.EVENT_ID)
        event = self._recorder.load('GET %s auth' % self.event_url)
        attendees = self._recorder.load('GET %s/attendees auth' % self.event_url)
        whoami = self._recorder.load('GET %s/whoami auth' % LFGSS_API)
        if not (event and attendees and whoami):
            self.skipTest('No signed-in recording of event %d. Run shoot --record with HARNESS_TOKEN.' % self.EVENT_ID)
        self.event = json.loads(event['body'])['data']
        self.attendees = json.loads(attendees['body'])['data']
        self.me = json.loads(whoami['body'])['data']
        self.make_steps()
        # Catch what the view sends the API: in replay the recorder answers
        # everything, so nothing leaves this process.
        self.api_writes = []
        answer = self._recorder.send

        def spy(adapter, request, **kwargs):
            if request.method != 'GET':
                self.api_writes.append((request.method, request.url, request.body))
            return answer(adapter, request, **kwargs)
        self._recorder.send = spy
        self.addCleanup(self._recorder.__dict__.pop, 'send', None)

    def event_data(self, attending):
        data = copy.deepcopy(self.event)
        # Upcoming: a month after the recording, so the RSVP controls show.
        data['when'] = (self.frozen + timedelta(days=31)).strftime('%Y-%m-%dT09:00:00Z')
        data['meta']['flags']['attending'] = attending
        data['rsvpAttend'] = self.event['rsvpAttend'] + (1 if attending else 0)
        return data

    def attendee_data(self, attending):
        data = copy.deepcopy(self.attendees)
        if attending:
            me = {k: self.me[k] for k in ('id', 'siteId', 'userId', 'profileName', 'visible', 'avatar')}
            me['meta'] = {'flags': {}, 'links': []}
            when = self.frozen.strftime('%Y-%m-%dT%H:%M:%SZ')
            data['attendees']['items'].append({'profileId': me['id'], 'profile': me, 'rsvp': 'yes', 'rsvpdOn': when,
                                               'meta': {'created': when, 'createdBy': me, 'flags': {}, 'links': []}})
            data['attendees']['total'] += 1
        return data

    def make_steps(self):
        get_event, get_attendees = 'GET %s auth' % self.event_url, 'GET %s/attendees auth' % self.event_url
        put = 'PUT %s/attendees auth' % self.event_url
        steps = {
            'invited': [_fixture(get_event, 200, self.event_data(False)),
                        _fixture(get_attendees, 200, self.attendee_data(False)),
                        # The same, for a guest.
                        _fixture(get_event.replace(' auth', ' anon'), 200, self.event_data(False)),
                        _fixture(get_attendees.replace(' auth', ' anon'), 200, self.attendee_data(False))],
            'going': [_fixture(put, 200, self.attendee_data(True)['attendees']['items'][-1:]),
                      _fixture(get_event, 200, self.event_data(True)),
                      _fixture(get_attendees, 200, self.attendee_data(True))],
            'not-going': [_fixture(put, 200, []),
                          _fixture(get_event, 200, self.event_data(False)),
                          _fixture(get_attendees, 200, self.attendee_data(False))],
        }
        for name, records in steps.items():
            for record in records:
                _write(os.path.join(self.stub_fixtures, name), record)

    def overlay(self, name):
        return OverlayRecording(self._recorder, self.stub_fixtures, name)

    def going(self, page):
        return page.locator('.mw-event-counts [stat]').first.inner_text()

    def my_row(self, page):
        return page.locator(MODAL + ' .mw-attendees a', has_text='@' + self.me['profileName'])

    def test_rsvp_yes_then_cant_make_it(self):
        path = '/events/%d/' % self.EVENT_ID
        action = path + 'rsvp/'
        going_before = str(self.event['rsvpAttend'])

        with self.overlay('invited'):
            page = self.open_bs5(path, signed_in=True)
            rsvp = page.locator('.mw-event-rsvp')
            yes = rsvp.get_by_role('button', name="Yes, I'm attending!")
            self.assertTrue(yes.is_visible())
            self.assertEqual(self.going(page), going_before)
            self.assertEqual(self.my_row(page).count(), 0)
            self.snap(page, 'BS5-11-signed-in-before')

        with self.overlay('going'):
            self.submit(page, yes.click, action)
            self.assert_on_bs5(page)
            self.assertEqual(urlsplit(page.url).path, path)
            method, url, body = self.api_writes[-1]
            self.assertEqual((method, url), ('PUT', self.event_url + '/attendees'))
            self.assertEqual(json.loads(body), [{'rsvp': 'yes', 'profileId': self.me['id']}])
            self.assertEqual(rsvp.get_by_role('heading').inner_text(), 'You are attending this event.')
            # The page loads the attendees again: the count, the avatars and the list show the RSVP.
            self.assertEqual(self.going(page), str(int(going_before) + 1))
            self.assertEqual(page.locator('.mw-event-people img[alt="Avatar for %s"]' % self.me['profileName']).count(), 1)
            self.assertEqual(self.my_row(page).count(), 1)
            self.snap(page, 'BS5-11-signed-in')

        with self.overlay('not-going'):
            self.submit(page, rsvp.get_by_role('button', name="Can't make it").click, action)
            method, url, body = self.api_writes[-1]
            self.assertEqual(json.loads(body), [{'rsvp': 'no', 'profileId': self.me['id']}])
            self.assertTrue(rsvp.get_by_role('button', name="Yes, I'm attending!").is_visible())
            self.assertEqual(self.going(page), going_before)
            self.assertEqual(self.my_row(page).count(), 0)
        self.assertEqual([w[0] for w in self.api_writes], ['PUT', 'PUT'])

    def test_guest_sees_sign_in_to_attend(self):
        with self.overlay('invited'):
            page = self.open_bs5('/events/%d/' % self.EVENT_ID)
        rsvp = page.locator('.mw-event-rsvp')
        self.assertEqual(rsvp.get_by_role('heading').inner_text(), 'Sign in to reserve your place in this event!')
        self.assertTrue(rsvp.get_by_role('button', name='Sign in or register to attend').is_visible())
        self.assertEqual(rsvp.locator('form').count(), 0)

    def test_expired_event_has_no_rsvp(self):
        page = self.open_bs5('/events/%d/' % self.EVENT_ID, signed_in=True)
        rsvp = page.locator('.mw-event-rsvp')
        self.assertIn('Follow this forum', rsvp.inner_text())
        self.assertEqual(rsvp.locator('form, button').count(), 0)


# Colour facts on an event page: the surround, the content and its links.
COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    image: getComputedStyle(document.body).backgroundImage,
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    place: rgb(document.querySelector('.mw-event-place'), 'color'),
    link: rgb(document.querySelector('.mw-breadcrumb a'), 'color'),
    metabarLink: rgb(document.querySelector('#mw-metabar .mw-module-author a'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
  };
}"""


class EspruinoBrandingTests(EventsTestCase):
    """Lane 10: Site branding holds on an event in light and dark."""

    def test_espruino_event_light_and_dark(self):
        site_link = colors.parse_hex('#4898AC')
        for mode in ('light', 'dark'):
            with self.subTest(mode=mode):
                page = self.open_bs5('/events/613/', host=ESPRUINO, color_mode=mode)
                facts = page.evaluate(COLOR_FACTS_JS)
                self.assertEqual(facts['theme'], mode)
                self.assertIn('url(', facts['image'], 'the Site background image')
                self.assertEqual(facts['logo'], 89)
                self.assertGreaterEqual(colors.contrast(facts['place'], facts['main']), 7)
                if mode == 'light':
                    light_surround = facts['surround']
                    for name in ('link', 'metabarLink'):
                        self.assertEqual(tuple(facts[name]), site_link, name)
                else:
                    self.assertEqual(facts['surround'], light_surround, 'the surround changed with the Color mode')
                    metabar = colors.dark_panel(tuple(facts['surround']))
                    for name in ('link', 'metabarLink'):
                        self.assertGreaterEqual(colors.contrast(facts[name], facts['main']), colors.AA, name)
                        self.assertGreaterEqual(colors.contrast(facts[name], metabar), colors.AA, name)
                self.snap(page, 'BS5-11-branding-%s' % mode)
                page.context.close()
