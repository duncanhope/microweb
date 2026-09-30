"""Interaction checks for the event form on Bootstrap 5 (BS5-12): forms/event.html
with eventForm.js and eventFormClasses.js.

Run with `python manage.py test --tag browser` after one `shoot --record`
(with HARNESS_TOKEN set, for the signed-in pages). Every page is asked for
with ?bs=5, so it renders from core/templates_bs5/.

What reaches the API: nothing is written. By the operator's decision the
checks that create or change an event run on made-up API answers only, in
replay mode: posting the create form (lane 7) and editing an event (lane 9).
The harness user has no event of its own, so the edit check makes one up
from the recorded test event manifest.RSVP_EVENT_ID with edit permission. A
real create and edit are manual checks for the operator before BS5-16.

The location search is made up too: the API's geocoder answers every query
with a 500 today (its upstream, MapQuest's open Nominatim, is gone), which
LocationSearchTests also covers. Islington CC's signed-in form (lane 10)
answers its whoami from a made-up recording, so no signed-in request reaches
another Site. The member search in the invite box is the mentions check's
recorded browser GET (conversations_browser_tests.MentionsTests).
"""
import copy
import json
import os
import re
import shutil
import tempfile
from urllib.parse import parse_qs, urlsplit

from django.test import override_settings

from core import colors
from core.harness import manifest, recorder
from core.harness.browser_tests import BrowserTestCase
from core.harness.conversations_browser_tests import _fixture, _write
from core.harness.lists_browser_tests import OverlayRecording

LFGSS = manifest.LFGSS
ISLINGTON = 'forum.islington.cc'
LFGSS_API = 'https://lfgss.microcosm.app/api/v1'
ISLINGTON_API = 'https://islingtoncc.microcosm.app/api/v1'
CREATE = '/microcosms/%d/create/event/' % manifest.EVENT_FORUM_ID
EDIT_EVENT_ID = manifest.RSVP_EVENT_ID
NEW_EVENT_ID = 99999002
NEW_COMMENT_ID = 99999003


def site_posts(page, host=LFGSS):
    """The (url, body) of every POST the page sends its own Site (Google's map posts too)."""
    sent = []
    page.on('request', lambda r: sent.append((r.url, r.post_data))
            if r.method == 'POST' and urlsplit(r.url).hostname == host else None)
    return sent


def form_fields(post_data):
    """The fields of a multipart form body, as {name: value}."""
    return dict(re.findall(r'name="([^"]+)"\r\n\r\n(.*?)\r\n--', post_data, re.S))


class EventFormTestCase(BrowserTestCase):

    def open_form(self, path=CREATE, **kwargs):
        page = self.open_bs5(path, signed_in=True, **kwargs)
        page.wait_for_function('() => document.querySelector("[data-mw-event-form]").dataset.mwReady !== undefined'
                               ' && document.querySelector("#map-canvas").mwMap')
        return page

    def stub_setup(self):
        """Made-up API answers: replay mode only, with the signed-in recording."""
        if self._recorder.mode != recorder.REPLAY:
            self.skipTest('The made-up event recordings run in replay mode only: they must never reach the API.')
        whoami = self._recorder.load('GET %s/whoami auth' % LFGSS_API)
        event = self._recorder.load('GET %s/events/%d auth' % (LFGSS_API, EDIT_EVENT_ID))
        if not (whoami and event):
            self.skipTest('No signed-in recording of event %d. Run shoot --record with HARNESS_TOKEN.' % EDIT_EVENT_ID)
        self.me = json.loads(whoami['body'])['data']
        self.base_event = json.loads(event['body'])['data']
        self.stub_dir = tempfile.mkdtemp(prefix='bs5-12-event-form-')
        self.addCleanup(shutil.rmtree, self.stub_dir, True)
        # Catch what the views send the API: in replay the recorder answers
        # everything, so nothing leaves this process.
        self.api_writes = []
        answer = self._recorder.send

        def spy(adapter, request, **kwargs):
            if request.method != 'GET':
                self.api_writes.append((request.method, request.url, request.body))
            return answer(adapter, request, **kwargs)
        self._recorder.send = spy
        self.addCleanup(self._recorder.__dict__.pop, 'send', None)

    def stub(self, name, records):
        for record in records:
            _write(os.path.join(self.stub_dir, name), record)
        return OverlayRecording(self._recorder, self.stub_dir, name)

    def author(self):
        me = {k: self.me[k] for k in ('id', 'siteId', 'userId', 'profileName', 'visible', 'avatar')}
        me['meta'] = {'flags': {}, 'links': []}
        return me

    def event(self, event_id, **values):
        """The recorded test event as the harness user's own, with no comments."""
        data = copy.deepcopy(self.base_event)
        data.update(id=event_id, **values)
        data['comments'].update(items=[], total=0, links=[])
        data['meta'].update(createdBy=self.author())
        data['meta']['permissions'].update(update=True, delete=True, owner=True)
        data['meta']['links'] = [{'rel': 'self', 'href': '/api/v1/events/%d' % event_id}]
        return data

    def attendees(self, people):
        return {'attendees': {'total': len(people), 'limit': 250, 'offset': 0, 'maxOffset': 0, 'totalPages': 1,
                              'page': 1, 'links': [], 'type': '/api/v1/attendees', 'items': people},
                'meta': {'flags': {}, 'links': []}}

    def attendee(self, profile, rsvp):
        when = self.frozen.strftime('%Y-%m-%dT%H:%M:%SZ')
        return {'profileId': profile['id'], 'profile': profile, 'rsvp': rsvp, 'rsvpdOn': when,
                'meta': {'created': when, 'createdBy': self.author(), 'flags': {}, 'links': []}}


class Bs5EventFormPagesTests(EventFormTestCase):

    def test_every_event_form_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('event_form'):
            with self.subTest(page=p.label):
                page = self.open_form(p.path)
                self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'))
                self.assertIn(page.locator('main h1').inner_text(), ('Post an event', 'Edit event'))
                page.context.close()

    def test_nothing_overflows_on_phones_and_tablets(self):
        for p in manifest.pages_for('event_form'):
            for width in (375, 768):
                with self.subTest(page=p.label, width=width):
                    page = self.open_form(p.path, width=width)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                    page.context.close()

    def test_edit_form_restores_the_event(self):
        page = self.open_form('/events/4488/edit/')
        self.assertEqual(page.get_by_label('What is the name of the event?').input_value(), 'The IKEA ride')
        # 2019-04-27 09:45 for 375 minutes, in Europe/London.
        self.assertTrue(page.locator('#date-type-single').is_checked())
        self.assertEqual(page.locator('#mw-event-start-date').input_value(), '2019-04-27')
        self.assertEqual(page.locator('#mw-event-start-time').input_value(), '09:45')
        self.assertEqual(page.locator('#mw-event-end-time').input_value(), '16:00')
        self.assertEqual(page.locator('#tz').input_value(), 'Europe/London')
        self.assertEqual(page.locator('#location').input_value(), 'IKEA Croydon')
        self.assertEqual(page.locator('.leaflet-marker-icon').count(), 1)
        # Everyone with an RSVP is listed, and stays: none has a remove button.
        people = page.locator('.mw-event-form-person')
        self.assertEqual(people.count(), 26)
        self.assertEqual(page.locator('.mw-event-form-invited .btn-close').count(), 0)
        self.assertTrue(page.locator('#attendee-limit-none').is_checked())
        self.assertTrue(page.locator('input[name=rsvpLimit]').is_disabled())


# ---------------------------------------------------------------------------
# Lane 7: pick a date and time with the native inputs, and post the form.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class CreateEventTests(EventFormTestCase):

    def setUp(self):
        self.stub_setup()

    def test_post_an_event(self):
        page = self.open_form()
        sent = site_posts(page)

        page.get_by_label('What is the name of the event?').fill('Harness ride')
        page.locator('#date-type-multiple').check()
        page.locator('#mw-event-start-date').fill('2026-11-14')
        page.locator('#mw-event-start-time').fill('19:30')
        page.locator('#mw-event-end-date').fill('2026-11-15')
        page.locator('#mw-event-end-time').fill('10:00')
        page.locator('#tz').select_option('Europe/Paris')
        self.assertEqual(page.locator('input[name=when]').input_value(), '2026-11-14T19:30:00Z')
        self.assertEqual(page.locator('input[name=duration]').input_value(), str(14 * 60 + 30))
        # A single day keeps the start date and the finish time.
        page.locator('#date-type-single').check()
        self.assertTrue(page.locator('#mw-event-end-date').is_hidden())
        page.locator('#mw-event-end-time').fill('21:00')
        self.assertEqual(page.locator('input[name=duration]').input_value(), '90')

        # Place the pin by clicking the map.
        page.locator('#location').fill('IKEA Croydon')
        page.locator('#map-canvas').click()
        for name in ('lat', 'lon', 'north', 'east', 'south', 'west'):
            self.assertRegex(page.locator('input[name=%s]' % name).input_value(), r'^-?\d', name)
        north, south = (float(page.locator('input[name=%s]' % n).input_value()) for n in ('north', 'south'))
        self.assertGreater(north, south)

        page.locator('#attendee-limit-max').check()
        limit = page.locator('input[name=rsvpLimit]')
        self.assertTrue(limit.evaluate('el => el === document.activeElement'))
        limit.fill('12')

        # Invite someone: the member search is the mentions check's recording.
        invite = page.get_by_role('combobox', name='Optional. Do you wish to invite others to your event?')
        invite.press_sequentially('du', delay=30)
        options = page.get_by_role('listbox', name='Members').get_by_role('option')
        options.first.wait_for()
        name = options.first.inner_text().strip()
        invite.press('Enter')
        self.assertEqual(page.locator('.mw-event-form-person').inner_text().strip(), name)
        invited = json.loads(page.locator('input[name=inviteObject]').input_value())
        self.assertEqual(page.locator('input[name=invite]').input_value(), str(invited[0]['id']))

        page.get_by_label('What is it you want to say?').fill('Posted from the harness')
        self.snap(page, 'BS5-12-check-a')

        event = self.event(NEW_EVENT_ID, title='Harness ride', when='2026-11-14T19:30:00Z', tz='Europe/Paris',
                           duration=90, where='IKEA Croydon', rsvpLimit=12, rsvpAttend=0)
        profile = {'id': invited[0]['id'], 'siteId': 1, 'userId': 1, 'profileName': name, 'visible': True,
                   'avatar': invited[0]['avatar'], 'meta': {'flags': {}, 'links': []}}
        event_url = '%s/events/%d' % (LFGSS_API, NEW_EVENT_ID)
        comment = {'id': NEW_COMMENT_ID, 'itemType': 'event', 'itemId': NEW_EVENT_ID, 'revisions': 1,
                   'markdown': 'Posted from the harness', 'html': '<p>Posted from the harness</p>\n',
                   'meta': {'created': '2026-09-30T12:00:00Z', 'createdBy': self.author(), 'flags': {},
                            'links': [], 'permissions': {}}}
        with self.stub('created', [
                _fixture('POST %s/events auth' % LFGSS_API, 200, event),
                _fixture('PUT %s/attendees auth' % event_url, 200, [self.attendee(profile, 'maybe')]),
                _fixture('POST %s/comments auth' % LFGSS_API, 200, comment),
                _fixture('GET %s auth' % event_url, 200, event),
                _fixture('GET %s/attendees?limit=250 auth' % event_url, 200,
                         self.attendees([self.attendee(profile, 'maybe')]))]):
            self.submit(page, page.get_by_role('button', name='Post event').click, '/events/%d/' % NEW_EVENT_ID)

        # The browser posted the fields core/forms/forms.py parses.
        url, body = sent[-1]
        self.assertEqual(urlsplit(url).path, CREATE)
        fields = form_fields(body)
        self.assertEqual(fields['when'], '2026-11-14T19:30:00Z')
        self.assertEqual((fields['duration'], fields['tz'], fields['rsvpLimit']), ('90', 'Europe/Paris', '12'))
        self.assertEqual(fields['invite'], str(invited[0]['id']))
        self.assertEqual(fields['firstcomment'], 'Posted from the harness')

        # And the API got an ISO 8601 start: the wall clock chosen, as Bootstrap 3 sent it.
        self.assertEqual([(m, urlsplit(u).path) for m, u, _ in self.api_writes], [
            ('POST', '/api/v1/events'), ('PUT', '/api/v1/events/%d/attendees' % NEW_EVENT_ID),
            ('POST', '/api/v1/comments')])
        payload = json.loads(self.api_writes[0][2])
        self.assertRegex(payload['when'], r'^2026-11-14T19:30:00([+-]\d\d:\d\d)?$')
        self.assertEqual((payload['title'], payload['tz'], payload['duration'], payload['rsvpLimit']),
                         ('Harness ride', 'Europe/Paris', 90, 12))
        self.assertEqual(json.loads(self.api_writes[1][2]), [{'rsvp': 'maybe', 'profileId': invited[0]['id']}])
        self.assertEqual(page.locator('main h1').inner_text(), 'Harness ride')
        self.snap(page, 'BS5-12-check-a-posted')

    def test_an_empty_title_or_a_missing_date_is_not_posted(self):
        page = self.open_form()
        posts = site_posts(page)
        page.locator('#mw-event-start-date').fill('')
        page.get_by_role('button', name='Post event').click()
        self.assertIn('is-invalid', page.get_by_label('What is the name of the event?').get_attribute('class'))
        self.assertIn('is-invalid', page.locator('#mw-event-start-date').get_attribute('class'))
        self.assertTrue(page.get_by_text('Please add a title').is_visible())
        self.assertEqual(page.locator('input[name=when]').input_value(), '')
        # To be decided needs no date.
        page.locator('#date-type-tbd').check()
        self.assertTrue(page.locator('[data-mw-when]').is_hidden())
        self.assertEqual(page.locator('input[name=duration]').input_value(), '')
        page.locator('#attendee-limit-max').check()
        page.get_by_label('What is the name of the event?').fill('Harness ride')
        page.get_by_role('button', name='Post event').click()
        self.assertIn('is-invalid', page.locator('input[name=rsvpLimit]').get_attribute('class'))
        self.assertTrue(page.get_by_text('From 1 to 999, please.').is_visible())
        self.assertEqual(posts, [])
        self.assertEqual(self.api_writes, [])


# ---------------------------------------------------------------------------
# Lane 8: the time zone list.

class TimeZoneTests(EventFormTestCase):

    def test_the_list_comes_from_intl_and_defaults_to_the_browser_zone(self):
        for zone in ('America/New_York', 'Asia/Kolkata'):
            with self.subTest(zone=zone):
                page = self.open_form(timezone_id=zone)
                facts = page.evaluate('''() => {
                  const select = document.getElementById('tz');
                  const values = [...select.options].map((o) => o.value);
                  const intl = Intl.supportedValuesOf('timeZone');
                  return { value: select.value, browser: Intl.DateTimeFormat().resolvedOptions().timeZone,
                           values, missing: intl.filter((z) => !values.includes(z)),
                           label: select.selectedOptions[0].textContent, first: select.options[0].textContent };
                }''')
                self.assertEqual(facts['value'], facts['browser'])
                self.assertEqual(facts['missing'], [])
                self.assertGreater(len(facts['values']), 300)
                self.assertEqual(len(set(facts['values'])), len(facts['values']))
                self.assertRegex(facts['label'], r'^\(GMT [+-]\d\d:\d\d\) ')
                self.assertRegex(facts['first'], r'^\(GMT -1[12]:00\) ')
                # The start defaults to the browser's wall clock at the next quarter hour.
                self.assertRegex(page.locator('#mw-event-start-time').input_value(), r'^\d\d:(00|15|30|45)$')
                page.locator('#tz').focus()
                self.snap(page, 'BS5-12-check-b' if zone == 'America/New_York' else 'BS5-12-check-b-kolkata')
                page.context.close()

    def test_an_edit_keeps_the_event_zone(self):
        page = self.open_form('/events/4488/edit/', timezone_id='America/New_York')
        self.assertEqual(page.locator('#tz').input_value(), 'Europe/London')
        # The start is the event's own wall clock, not the browser's.
        self.assertEqual(page.locator('#mw-event-start-time').input_value(), '09:45')


# ---------------------------------------------------------------------------
# Lane 9: edit an event as the harness user, answered from made-up fixtures.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class EditEventTests(EventFormTestCase):

    def setUp(self):
        self.stub_setup()

    def test_edit_an_event(self):
        path = '/events/%d/edit/' % EDIT_EVENT_ID
        event_url = '%s/events/%d' % (LFGSS_API, EDIT_EVENT_ID)
        going = [self.attendee(dict(self.author(), id=self.me['id'] + n, profileName='rider%d' % n), 'yes')
                 for n in (1, 2, 3)]
        # A three-day event in Sydney, with a place on the map.
        before = self.event(EDIT_EVENT_ID, when='2026-12-04T09:00:00Z', duration=3 * 24 * 60 - 120,
                            tz='Australia/Sydney', where='Sydney, Australia', lat=-33.8688, lon=151.2093,
                            north=-33.85, east=151.23, south=-33.89, west=151.19, rsvpLimit=20)
        after = dict(before, title='Test event - edited', when='2026-12-05T08:00:00Z', duration=2 * 24 * 60)
        get_event, get_attendees = 'GET %s auth' % event_url, 'GET %s/attendees?limit=250 auth' % event_url

        with self.stub('before', [_fixture(get_event, 200, before),
                                  _fixture(get_attendees, 200, self.attendees(going))]):
            page = self.open_form(path, timezone_id='Europe/London')
        sent = site_posts(page)

        self.assertEqual(page.get_by_label('What is the name of the event?').input_value(), before['title'])
        self.assertTrue(page.locator('#date-type-multiple').is_checked())
        self.assertEqual([page.locator('#mw-event-%s' % n).input_value() for n in
                          ('start-date', 'start-time', 'end-date', 'end-time')],
                         ['2026-12-04', '09:00', '2026-12-07', '07:00'])
        self.assertEqual(page.locator('#tz').input_value(), 'Australia/Sydney')
        self.assertEqual(page.locator('#location').input_value(), 'Sydney, Australia')
        self.assertEqual(page.locator('input[name=rsvpLimit]').input_value(), '20')
        self.assertEqual(page.locator('.mw-event-form-person').all_inner_texts(), ['rider1', 'rider2', 'rider3'])
        self.assertEqual(page.locator('.mw-event-form-invited .btn-close').count(), 0)
        self.assertTrue(page.locator('.leaflet-marker-icon').is_visible())
        self.assertEqual(page.locator('#mw-editor-firstcomment').count(), 0)

        page.get_by_label('What is the name of the event?').fill('Test event - edited')
        page.locator('#mw-event-start-date').fill('2026-12-05')
        page.locator('#mw-event-start-time').fill('08:00')
        page.locator('#mw-event-end-time').fill('08:00')
        # The reason is needed.
        page.get_by_role('button', name='Edit event').click()
        self.assertEqual(sent, [])
        page.get_by_label('Reason for editing').fill('Moved a day')
        self.snap(page, 'BS5-12-signed-in')

        with self.stub('after', [_fixture('POST %s?method=PUT auth' % event_url, 200, after),
                                 _fixture(get_event, 200, after),
                                 _fixture(get_attendees, 200, self.attendees(going))]):
            self.submit(page, page.get_by_role('button', name='Edit event').click, '/events/%d/' % EDIT_EVENT_ID)

        fields = form_fields(sent[-1][1])
        self.assertEqual(urlsplit(sent[-1][0]).path, path)
        self.assertEqual((fields['when'], fields['duration'], fields['tz']),
                         ('2026-12-05T08:00:00Z', str(2 * 24 * 60), 'Australia/Sydney'))
        self.assertEqual((fields['lat'], fields['north']), ('-33.8688', '-33.85'))
        self.assertEqual(fields['editReason'], 'Moved a day')
        self.assertEqual(len(self.api_writes), 1)
        method, url, body = self.api_writes[0]
        self.assertEqual((method, urlsplit(url).path, parse_qs(urlsplit(url).query)),
                         ('POST', '/api/v1/events/%d' % EDIT_EVENT_ID, {'method': ['PUT']}))
        payload = json.loads(body)
        self.assertRegex(payload['when'], r'^2026-12-05T08:00:00')
        self.assertEqual((payload['id'], payload['title'], payload['duration'], payload['meta']),
                         (EDIT_EVENT_ID, 'Test event - edited', 2 * 24 * 60, {'editReason': 'Moved a day'}))
        self.assertEqual(page.locator('main h1').inner_text(), 'Test event - edited')
        self.snap(page, 'BS5-12-signed-in-after')


# ---------------------------------------------------------------------------
# The location search, and "to be decided".

class LocationSearchTests(EventFormTestCase):

    def setUp(self):
        self.stub_setup()

    def geocode(self, answer, status=200):
        record = _fixture('GET %s/geocode?q=IKEA+Croydon auth' % LFGSS_API, status, None)
        record['body'] = json.dumps(answer)
        return self.stub('geocode-%d' % status, [record])

    def test_show_on_map_finds_the_place(self):
        page = self.open_form()
        place = {'place_id': 1, 'lat': '51.3806', 'lon': '-0.1180',
                 'boundingbox': ['51.3790', '51.3822', '-0.1210', '-0.1150']}
        with self.geocode(place):
            page.locator('#location').fill('IKEA\nCroydon')
            page.get_by_role('button', name='Show on map').click()
            page.wait_for_function('() => document.querySelector("input[name=lat]").value')
        self.assertAlmostEqual(float(page.locator('input[name=lat]').input_value()), 51.3806)
        self.assertAlmostEqual(float(page.locator('input[name=lon]').input_value()), -0.1180)
        self.assertEqual(page.locator('.leaflet-marker-icon').count(), 1)
        self.assertEqual(page.locator('[data-mw-locate-status]').inner_text(), '')

        # To be decided hides the place and clears it.
        page.locator('#location-type-tbd').check()
        self.assertTrue(page.locator('[data-mw-where]').is_hidden())
        self.assertEqual(page.locator('input[name=lat]').input_value(), '')
        self.assertEqual(page.locator('#location').input_value(), '')
        self.assertEqual(page.locator('.leaflet-marker-icon').count(), 0)
        page.locator('#location-type-place').check()
        self.assertTrue(page.locator('#map-canvas').is_visible())

    def test_a_failed_search_says_so(self):
        # The API's answer today, recorded on 2026-09-30.
        error = {'error': ['Get "http://open.mapquestapi.com/nominatim/v1/search.php?format=json&limit=1'
                           '&q=IKEA+Croydon": dial tcp: lookup open.mapquestapi.com: no such host']}
        page = self.open_form()
        with self.geocode(error, 500):
            page.locator('#location').fill('IKEA Croydon')
            page.get_by_role('button', name='Show on map').click()
            status = page.locator('[data-mw-locate-status]')
            page.wait_for_function('(s) => document.querySelector(s).textContent.includes("not found")',
                                   arg='[data-mw-locate-status]')
        self.assertEqual(status.inner_text(), 'That place was not found. Click the map to place the pin.')
        self.assertEqual(page.locator('input[name=lat]').input_value(), '')


# ---------------------------------------------------------------------------
# Lane 10: Islington CC's branding around the form, light and dark.

COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    label: rgb(document.querySelector('.mw-event-form legend'), 'color'),
    sublabel: rgb(document.querySelector('.mw-event-form-sublabel'), 'color'),
    input: rgb(document.querySelector('#title'), 'color'),
    inputBg: rgb(document.querySelector('#title'), 'backgroundColor'),
    link: rgb(document.querySelector('.mw-breadcrumb a'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
    mapScheme: getComputedStyle(document.querySelector('#map-canvas')).colorScheme,
  };
}"""


class IslingtonBrandingTests(EventFormTestCase):

    def setUp(self):
        self.stub_setup()

    def test_islington_event_form_light_and_dark(self):
        # A made-up Islington whoami, so no signed-in request reaches that Site.
        me = dict(self.me, siteId=0)
        site_link = colors.parse_hex('#185945')
        surround = colors.parse_hex('#bfc3c5')
        with self.stub('islington', [_fixture('GET %s/whoami auth' % ISLINGTON_API, 200, me)]):
            for mode in ('light', 'dark'):
                with self.subTest(mode=mode):
                    page = self.open_bs5('/microcosms/1/create/event/', host=ISLINGTON, signed_in=True,
                                         color_mode=mode)
                    page.wait_for_function('() => document.querySelector("#map-canvas").mwMap')
                    facts = page.evaluate(COLOR_FACTS_JS)
                    self.assertEqual(facts['theme'], mode)
                    self.assertEqual(tuple(facts['surround']), surround, 'the Site surround')
                    self.assertEqual(facts['logo'], 89)
                    self.assertEqual(facts['mapScheme'], 'light')
                    self.assertGreaterEqual(colors.contrast(facts['label'], facts['main']), 7)
                    self.assertGreaterEqual(colors.contrast(facts['sublabel'], facts['main']), colors.AA)
                    self.assertGreaterEqual(colors.contrast(facts['input'], facts['inputBg']), 7)
                    if mode == 'light':
                        self.assertEqual(tuple(facts['link']), site_link)
                    else:
                        self.assertGreaterEqual(colors.contrast(facts['link'], facts['main']), colors.AA)
                    self.snap(page, 'BS5-12-branding-%s' % mode)
                    page.context.close()
        self.assertEqual(self.api_writes, [])
