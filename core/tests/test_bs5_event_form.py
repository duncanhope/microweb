"""The event form on Bootstrap 5 (BS5-12): forms/event.html, with eventForm.js,
eventFormClasses.js and the _event_form.scss partial.

The create and edit forms render through events/views.py with their API
answers made up here. The form posts the fields core/forms/forms.py already
parses, so the tests also post what the native date and time inputs make
through the view, and check what would reach the API."""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.forms.forms import EventCreate
from events import views

REPO = Path(settings.PROJECT_ROOT).parent
DATA = Path(__file__).resolve().parent / 'data'
PARTIAL = REPO / 'core' / 'static' / 'themes' / '1' / 'scss' / '_event_form.scss'
SCRIPTS = REPO / 'core' / 'static' / 'js' / 'bs5'

# Every template the family owns in core/templates_bs5/.
FAMILY = ['forms/event.html', 'google_maps_loader.html']
FAMILY_SCRIPTS = ['eventForm.js', 'eventFormClasses.js']

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')

EVENT_URL, ATTENDEES_URL, SITE_URL, WHOAMI_URL = 'event', 'attendees', 'site', 'whoami'


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


def compose_when(date, time):
    """What eventFormClasses.js composeWhen makes of the native inputs' values."""
    return '%sT%s:00Z' % (date, time[:5])


def person(n, rsvp='yes'):
    profile = {'id': 100 + n, 'siteId': 1, 'userId': 100 + n, 'profileName': 'rider%d' % n, 'visible': True,
               'avatar': '/api/v1/files/abc%d' % n, 'meta': {'flags': {}, 'links': []}}
    return {'profileId': 100 + n, 'profile': profile, 'rsvp': rsvp, 'rsvpdOn': '2026-09-01T10:00:00Z',
            'meta': {'created': '2026-09-01T10:00:00Z', 'flags': {}, 'links': []}}


def attendees(people):
    return {'attendees': {'total': len(people), 'limit': 250, 'offset': 0, 'maxOffset': 0, 'totalPages': 1,
                          'page': 1, 'links': [], 'type': '', 'items': people},
            'meta': {'flags': {}, 'links': []}}


def request(path, method='get', data=None):
    request = getattr(RequestFactory(), method)(path, data or {})
    request.access_token = 'token'
    request.whoami_url = WHOAMI_URL
    request.site_url = SITE_URL
    request.view_requests = []
    request.color_mode = 'auto'
    return request


class Bs5EventFormTests(SimpleTestCase):

    def setUp(self):
        self.event = load('event_with_comment.json')
        self.event.update(when='2026-10-10T19:00:00Z', duration=120, tz='Europe/London', where='IKEA Croydon',
                          lat=51.38, lon=-0.12, north=51.39, east=-0.11, south=51.37, west=-0.13, rsvpLimit=30)
        self.people = [person(1), person(2, 'maybe')]
        self.responses = {SITE_URL: load('site.json'), WHOAMI_URL: load('whoami.json')}

    def patched(self):
        return [mock.patch.object(views.fetch, 'map', return_value=[]),
                mock.patch.object(views, 'response_list_to_dict', return_value=self.responses)]

    def run_view(self, view, req, *args):
        patches = self.patched()
        for p in patches:
            p.start()
        try:
            return view(req, *args)
        finally:
            for p in patches:
                p.stop()

    def create_page(self, bs=5, method='get', data=None):
        response = self.run_view(views.create, request('/microcosms/1/create/event/?bs=%d' % bs, method, data), '1')
        self.assertEqual(response.status_code, 200)
        return response.content.decode('utf-8')

    def edit_page(self, bs=5):
        from core.api.resources import AttendeeList, Event
        event = Event.from_api_response(self.event)
        with mock.patch.object(views.Event, 'retrieve', return_value=event), \
                mock.patch.object(views.Event, 'get_attendees', return_value=AttendeeList(attendees(self.people))):
            response = self.run_view(views.edit, request('/events/2/edit/?bs=%d' % bs), '2')
        self.assertEqual(response.status_code, 200)
        return response.content.decode('utf-8')

    def assert_bootstrap_5_only(self, html):
        for old in ('data-toggle=', 'data-target=', 'data-dismiss=', 'sprite-', 'glyphicon', '$(',
                    'moment', 'jstz', 'timezones.min.js', 'eventFormClasses.js?', 'js/eventForm.js',
                    'peopleWidget.js', 'formValidator.js', 'datepicker'):
            self.assertNotIn(old, html)

    # The family ---------------------------------------------------------------------

    def test_every_family_template_is_served_from_the_bs5_tree(self):
        for name in FAMILY:
            with self.subTest(template=name):
                origin = engines['bs5'].get_template(name).origin.name
                self.assertEqual(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR), name)

    def test_both_forms_render_on_bootstrap_5_without_bootstrap_3_or_jquery(self):
        for name, html in (('create', self.create_page()), ('edit', self.edit_page())):
            with self.subTest(form=name):
                self.assertIn('bs5.min.css', html)
                self.assertIn('data-mw-event-form', html)
                self.assert_bootstrap_5_only(html)
                self.assertIn('<script type="module" src="/static/js/bs5/eventForm.js"></script>', html)
                self.assertIn('3rd/leaflet/0.7.7/leaflet.js', html)
                self.assertIn('v: "weekly"', html)

    def test_partial_has_no_colour_literals(self):
        self.assertEqual(COLOUR_LITERAL.findall(PARTIAL.read_text()), [])
        self.assertIn('@import "event_form";', (PARTIAL.parent / 'site.scss').read_text())

    def test_scripts_are_modules_without_jquery_moment_or_jstz(self):
        for name in FAMILY_SCRIPTS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text()
                code = re.sub(r'(?m)^\s*//.*$', '', source)
                self.assertIsNone(re.search(r'\$\(|\$\.|jQuery|moment|jstz|datepicker', code))
                self.assertRegex(source, r'(?m)^(import|export) ')

    def test_time_zones_come_from_intl(self):
        source = (SCRIPTS / 'eventFormClasses.js').read_text()
        self.assertIn("Intl.supportedValuesOf('timeZone')", source)
        self.assertIn('Intl.DateTimeFormat().resolvedOptions().timeZone', source)

    def test_bootstrap_3_form_is_unchanged(self):
        html = self.create_page(bs=3)
        self.assertNotIn('bs5.min.css', html)
        self.assertIn('js/eventFormClasses.js?v20260930', html)
        self.assertIn('3rd/jsTimezoneDetect/1.0.6/jstz.min.js', html)
        self.assertIn('sprite sprite-search-small', html)

    # The create form -----------------------------------------------------------------

    def test_create_form(self):
        html = self.create_page()
        self.assertIn('<h1 class="mw-item-title mb-3">Post an event</h1>', html)
        self.assertIn('<input type="hidden" name="microcosmId" value="1"', html)
        self.assertIn('<input type="hidden" name="when" value="">', html)
        self.assertIn('<input type="hidden" name="duration" value="">', html)
        self.assertIn('maxlength="150" required value="">', html)
        self.assertIn('<div class="invalid-feedback">Please add a title</div>', html)
        self.assertIn('<input type="date" class="form-control" id="mw-event-start-date" required>', html)
        self.assertIn('<input type="time" class="form-control" id="mw-event-start-time" aria-label="Start time" '
                      'required>', html)
        self.assertIn('<input type="time" class="form-control" id="mw-event-end-time" required>', html)
        # The browser fills the list and chooses its own zone.
        self.assertRegex(html, r'<select id="tz" name="tz" class="form-select" required data-mw-tz>\s*</select>')
        self.assertIn('id="map-canvas" class="mw-event-form-map" data-mw-event-form-map data-thunderforest-key=',
                      html)
        self.assertIn('name="rsvpLimit" min="1" max="999"', html)
        self.assertIn('value="0" disabled>', html)
        self.assertIn('data-mw-invite data-mw-invited="">', html)
        self.assertIn('<input type="hidden" name="invite" value="">', html)
        self.assertIn('<label class="form-label" for="mw-editor-firstcomment">What is it you want to say?</label>',
                      html)
        self.assertIn('name="firstcomment"', html)
        self.assertIn('>Post event</button>', html)
        self.assertNotIn('editReason', html)
        self.assertNotIn(' data-edit', html)

    def test_icons_are_inline_svg(self):
        html = self.create_page()
        picker = re.search(r'<span class="input-group-text">(.*?)</span>', html, re.S).group(1)
        self.assertIn('bi-search', picker)
        self.assertIn('aria-hidden="true"', picker)

    # The edit form -------------------------------------------------------------------

    def test_edit_form_carries_the_event(self):
        html = self.edit_page()
        self.assertIn('<h1 class="mw-item-title mb-3">Edit event</h1>', html)
        self.assertIn(' data-edit>', html)
        self.assertIn('<input type="hidden" name="id" value="2"', html)
        # The wall clock the API gave, with the Z Bootstrap 3 sent: eventForm.js splits it into the inputs.
        self.assertIn('<input type="hidden" name="when" value="2026-10-10T19:00:00Z">', html)
        self.assertIn('<input type="hidden" name="duration" value="120">', html)
        self.assertIn('<option value="Europe/London" selected>Europe/London</option>', html)
        for name, value in (('lat', '51.38'), ('lon', '-0.12'), ('north', '51.39'), ('east', '-0.11'),
                            ('south', '51.37'), ('west', '-0.13')):
            self.assertIn('<input type="hidden" name="%s" value="%s">' % (name, value), html)
        self.assertIn('>IKEA Croydon</textarea>', html)
        self.assertIn('id="attendee-limit-max" value="1" checked>', html)
        self.assertIn('name="rsvpLimit" min="1" max="999" inputmode="numeric" aria-label="Max number of attendees" '
                      'value="30">', html)
        # Nothing has been posted, so the empty reason is not an error yet.
        self.assertIn('class="form-control" id="editReason" name="editReason"', html)
        self.assertNotIn('is-invalid', html)
        self.assertIn('>Edit event</button>', html)
        self.assertNotIn('firstcomment', html)

    def test_edit_form_lists_everyone_with_an_rsvp(self):
        self.people = [person(n) for n in range(30)]
        html = self.edit_page()
        invited = re.search(r'data-mw-invited="([^"]*)"', html).group(1)
        people = json.loads(invited.replace('&quot;', '"'))
        self.assertEqual(len(people), 30)
        self.assertEqual(people[0], {'id': 100, 'profileName': 'rider0', 'avatar': '/api/v1/files/abc0',
                                     'sticky': 'true'})

    def test_an_event_without_a_date_or_place(self):
        for key in ('when', 'duration', 'where', 'lat', 'lon', 'north', 'east', 'south', 'west'):
            self.event.pop(key)
        html = self.edit_page()
        self.assertIn('<input type="hidden" name="when" value="">', html)
        self.assertIn('<input type="hidden" name="lat" value="">', html)
        self.assertIn('placeholder="Eg. Street, station, landmark, country..." maxlength="150" '
                      'aria-label="Location"></textarea>', html)

    # Posting -----------------------------------------------------------------------

    def post_data(self, **overrides):
        data = {'microcosmId': '1', 'title': 'A test ride', 'when': compose_when('2026-10-10', '19:00'),
                'duration': '120', 'tz': 'Europe/London', 'where': 'IKEA Croydon', 'lat': '51.38', 'lon': '-0.12',
                'north': '51.39', 'east': '-0.11', 'south': '51.37', 'west': '-0.13', 'rsvpLimit': '30',
                'invite': '', 'inviteObject': '', 'firstcomment': '',
                # Sent, and ignored, as on Bootstrap 3.
                'date-type': '1', 'location-type': '1', 'attendee-limit-option': '1'}
        data.update(overrides)
        return data

    def test_native_date_and_time_values_parse_through_the_form(self):
        for date, time in (('2026-10-10', '19:00'), ('2026-10-10', '19:00:30'), ('2027-01-01', '00:15')):
            with self.subTest(date=date, time=time):
                form = EventCreate(self.post_data(when=compose_when(date, time)))
                self.assertTrue(form.is_valid(), form.errors)
                when = form.cleaned_data['when']
                self.assertEqual(when.replace(tzinfo=None), datetime.fromisoformat('%sT%s' % (date, time[:5])))
        # To be decided: no date and no duration.
        form = EventCreate(self.post_data(when='', duration=''))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['when'])
        self.assertIsNone(form.cleaned_data['duration'])

    def test_posting_the_create_form_sends_the_event_to_the_api(self):
        created = mock.Mock(id=77)
        with mock.patch.object(views.Event, 'create', autospec=True, return_value=created) as create:
            response = self.run_view(views.create, request('/microcosms/1/create/event/?bs=5', 'post',
                                                           self.post_data()), '1')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/events/77/')
        payload = create.call_args[0][0].as_dict()
        self.assertEqual(payload['when'].replace(tzinfo=None), datetime(2026, 10, 10, 19, 0))
        self.assertEqual((payload['tz'], payload['duration'], payload['rsvpLimit']), ('Europe/London', 120, 30))
        self.assertEqual((payload['lat'], payload['north'], payload['west']), (51.38, 51.39, -0.13))

    def test_a_form_sent_back_with_errors_keeps_what_was_chosen(self):
        chosen = [{'id': 101, 'profileName': 'rider1', 'avatar': ''}]
        html = self.create_page(method='post', data=self.post_data(title='', inviteObject=json.dumps(chosen)))
        self.assertIn('class="form-control is-invalid" id="title"', html)
        self.assertIn('<div class="invalid-feedback">Please add a title</div>', html)
        self.assertIn('<input type="hidden" name="when" value="2026-10-10T19:00:00Z">', html)
        self.assertIn('<option value="Europe/London" selected>Europe/London</option>', html)
        self.assertIn('data-mw-invited="[{&quot;id&quot;: 101, &quot;profileName&quot;: &quot;rider1&quot;',
                      html)

    def test_a_bad_date_is_shown_by_the_dates(self):
        html = self.create_page(method='post', data=self.post_data(when='10/10/2026'))
        self.assertIn('<div class="invalid-feedback d-block mb-2">Please check the date and time formatting</div>',
                      html)
