"""The events family on Bootstrap 5 (BS5-11): event.html, event_header_small.html,
event_header_large.html, modal_event_attendees.html and the event row
(block_event.html, BS5-07), with eventMap.js, leafletGoogle.js and the
_events.scss partial.

Pages render through events/views.py single with its API answers made up
here, so the header gets the view's own dates, attendees and RSVP state."""
import copy
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Event
from core.tests.test_bs5_base import make_site
from events import views

REPO = Path(settings.PROJECT_ROOT).parent
DATA = Path(__file__).resolve().parent / 'data'
PARTIAL = REPO / 'core' / 'static' / 'themes' / '1' / 'scss' / '_events.scss'
SCRIPTS = REPO / 'core' / 'static' / 'js' / 'bs5'

# Every template the family owns in core/templates_bs5/.
FAMILY = ['event.html', 'event_header_small.html', 'event_header_large.html', 'modal_event_attendees.html',
          'block_event.html']
FAMILY_SCRIPTS = ['eventMap.js', 'leafletGoogle.js']

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')

EVENT_URL, ATTENDEES_URL, SITE_URL, WHOAMI_URL = 'event', 'attendees', 'site', 'whoami'


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


def stamp(when):
    return when.strftime('%Y-%m-%dT%H:%M:%SZ')


def person(n):
    return {'id': 100 + n, 'siteId': 1, 'userId': 100 + n, 'profileName': 'rider%d' % n, 'visible': True,
            'avatar': '', 'meta': {'flags': {}, 'links': []}}


def attendee(n, rsvp='yes'):
    return {'profileId': 100 + n, 'profile': person(n), 'rsvp': rsvp, 'rsvpdOn': '2026-09-01T10:00:00Z',
            'meta': {'created': '2026-09-01T10:00:00Z', 'flags': {}, 'links': []}}


class Bs5EventsTests(SimpleTestCase):

    def setUp(self):
        self.event = load('event_with_comment.json')
        # Upcoming, two hours, with a place on the map.
        start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=10)
        self.event.update(when=stamp(start), duration=120, where='IKEA Croydon', lat=51.38, lon=-0.12,
                          north=51.39, west=-0.13, south=51.37, east=-0.11, rsvpLimit=0)
        self.event.pop('rsvpSpaces', None)
        self.people = []

    def page(self, member=False, path='/events/2/?bs=5'):
        """The event page as events/views.py single renders it."""
        request = RequestFactory().get(path)
        request.access_token = 'token' if member else None
        request.whoami_url = WHOAMI_URL if member else ''
        request.site_url = SITE_URL
        request.view_requests = []
        request.color_mode = 'auto'
        # A later comment page, as the API answers ?offset=25.
        self.event['comments']['page'] = 2 if 'offset=' in path else 1
        going = sum(1 for a in self.people if a['rsvp'] == 'yes')
        if going:
            self.event['rsvpAttend'] = going
        responses = {
            EVENT_URL: self.event,
            ATTENDEES_URL: {'attendees': {'total': len(self.people), 'limit': 25, 'offset': 0, 'maxOffset': 0,
                                          'totalPages': 1, 'page': 1, 'links': [], 'type': '', 'items': self.people},
                            'meta': {'flags': {}, 'links': []}},
            SITE_URL: load('site.json'),
            WHOAMI_URL: load('whoami.json'),
        }
        with mock.patch.object(views.Event, 'build_request', return_value=(EVENT_URL, {}, {})), \
                mock.patch.object(views.Event, 'build_attendees_request', return_value=(ATTENDEES_URL, {}, {})), \
                mock.patch.object(views.fetch, 'map', return_value=[]), \
                mock.patch.object(views, 'response_list_to_dict', return_value=responses):
            response = views.single(request, '2')
        self.assertEqual(response.status_code, 200)
        return response.content.decode('utf-8')

    def set(self, **values):
        self.event.update(values)

    def assert_bootstrap_5_only(self, html):
        self.assertNotIn('data-toggle=', html)
        self.assertNotIn('data-target=', html)
        self.assertNotIn('data-dismiss=', html)
        self.assertNotIn('sprite-', html)
        self.assertNotIn('glyphicon', html)
        self.assertNotIn('$(', html)

    def rsvp_html(self, html):
        return re.search(r'<div class="mw-event-rsvp">(.*?)\n\t\t</div>', html, re.S).group(1)

    # The family ---------------------------------------------------------------------

    def test_every_family_template_is_served_from_the_bs5_tree(self):
        for name in FAMILY:
            with self.subTest(template=name):
                origin = engines['bs5'].get_template(name).origin.name
                self.assertEqual(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR), name)

    def test_the_page_renders_on_bootstrap_5_without_bootstrap_3_or_jquery(self):
        self.people = [attendee(n) for n in range(7)] + [attendee(9, 'maybe')]
        for member in (False, True):
            for path in ('/events/2/?bs=5', '/events/2/?bs=5&offset=25'):
                with self.subTest(member=member, path=path):
                    html = self.page(member=member, path=path)
                    self.assertIn('bs5.min.css', html)
                    self.assertIn('class="mw-event', html)
                    self.assert_bootstrap_5_only(html)

    def test_every_family_template_renders_alone_without_bootstrap_3(self):
        content = Event.from_api_response(self.event)
        context = {'site': make_site(), 'user': None, 'content': content, 'item': content,
                   'event_dates': {'type': 'single', 'end': content.when}, 'attendees_yes': [], 'attendees_invited': []}
        request = RequestFactory().get('/events/2/')
        for name in FAMILY:
            if name == 'event.html':
                continue
            with self.subTest(template=name):
                self.assert_bootstrap_5_only(engines['bs5'].get_template(name).render(context, request))

    def test_partial_has_no_colour_literals(self):
        self.assertEqual(COLOUR_LITERAL.findall(PARTIAL.read_text()), [])
        self.assertIn('@import "events";', (PARTIAL.parent / 'site.scss').read_text())

    def test_scripts_are_modules_without_jquery_or_moment(self):
        for name in FAMILY_SCRIPTS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text()
                code = re.sub(r'(?m)^\s*//.*$', '', source)
                self.assertIsNone(re.search(r'\$\(|\$\.|jQuery|moment', code))
                self.assertRegex(source, r'(?m)^(import|export) ')

    # The header -------------------------------------------------------------------

    def test_first_page_with_a_place_has_the_map(self):
        html = self.page()
        self.assertIn('mw-event mw-event-large', html)
        self.assertIn('data-mw-event-map data-lat="51.38" data-lon="-0.12" data-north="51.39" data-west="-0.13" '
                      'data-south="51.37" data-east="-0.11"', html)
        self.assertIn('3rd/leaflet/0.7.7/leaflet.css', html)
        self.assertIn('3rd/leaflet/0.7.7/leaflet.js', html)
        self.assertIn('<script type="module" src="/static/js/bs5/eventMap.js">', html)
        self.assertNotIn('js/eventMap.js', html.replace('js/bs5/eventMap.js', ''))

    def test_later_pages_and_events_without_a_place_have_no_map(self):
        for label, path, change in (('later page', '/events/2/?bs=5&offset=25', {}),
                                    ('no place', '/events/2/?bs=5', {'lat': None, 'lon': None})):
            with self.subTest(label):
                self.set(**change)
                html = self.page(path=path)
                self.assertNotIn('mw-event-large', html)
                self.assertNotIn('data-mw-event-map', html)
                self.assertNotIn('leaflet', html)
                self.assertEqual(html.count('class="mw-event-fact"'), 3)

    def test_date_time_and_place(self):
        when = Event.from_api_response(self.event).when
        html = self.page()
        self.assertIn('<span class="mw-event-day">%s</span>' % when.day, html)
        self.assertIn('%s <strong>%s</strong>' % (when.strftime('%A'), when.strftime('%B %Y')), html)
        self.assertRegex(html, r'<span class="mw-event-time"><time class="plain" itemprop="duration" '
                               r'datetime="P120M">\d+:\d\d [AP]M - \d+:\d\d [AP]M</time>')
        self.assertIn('<span itemprop="name">IKEA Croydon</span>', html)
        self.assertIn('{0}'.format('bi-calendar-event'), html)
        self.assertIn('bi-geo-alt', html)

    def test_a_multi_day_event_shows_its_end(self):
        self.set(duration=60 * 50)
        html = self.page()
        self.assertIn('bi-calendar-range', html)
        self.assertIn('itemprop="endDate"', html)
        self.assertEqual(html.count('class="mw-event-fact"'), 3)

    def test_to_be_decided(self):
        self.set(when=None, where=None, lat=None, lon=None)
        html = self.page()
        self.assertEqual(html.count('<abbr title="To be determined">TBD</abbr>'), 2)

    # Attendees and the modal ------------------------------------------------------------

    def test_five_avatars_then_more_and_the_modal(self):
        self.people = [attendee(n) for n in range(8)] + [attendee(20, 'maybe'), attendee(21, 'maybe')]
        html = self.page()
        people = re.search(r'<ul class="list-unstyled mw-event-people">(.*?)</ul>', html, re.S).group(1)
        self.assertEqual(people.count('data-bs-toggle="tooltip"'), 5)
        self.assertIn('title="@rider0"', people)
        self.assertNotIn('rider5', people)
        self.assertIn('data-bs-target="#modal-event-attendees" aria-label="Everyone going and invited">+3</button>',
                      people)
        counts = re.search(r'<button type="button" class="mw-event-counts".*?</button>', html, re.S).group(0)
        self.assertIn('data-bs-toggle="modal" data-bs-target="#modal-event-attendees"', counts)
        self.assertIn('Going <span stat="8">8</span>', counts)
        self.assertIn('Invited <span stat="2">2</span>', counts)

        modal = re.search(r'<div id="modal-event-attendees".*', html, re.S).group(0)
        self.assertIn('class="modal fade" tabindex="-1" aria-labelledby="modal-event-attendees-title"', modal)
        self.assertIn('data-bs-dismiss="modal"', modal)
        rows = re.findall(r'<li><a href="/profiles/(\d+)/">', modal)
        self.assertEqual(rows, [str(100 + n) for n in list(range(8)) + [20, 21]], 'going first, then invited')
        self.assertEqual(modal.count('<em>invited</em>'), 2)

    def test_only_invited_shows_the_invited(self):
        self.people = [attendee(n, 'maybe') for n in range(7)]
        html = self.page()
        people = re.search(r'<ul class="list-unstyled mw-event-people">(.*?)</ul>', html, re.S).group(1)
        self.assertEqual(people.count('data-bs-toggle="tooltip"'), 5)
        self.assertIn('>+2</button>', people)

    def test_the_places_bar(self):
        self.set(rsvpLimit=100, rsvpSpaces=100)
        html = self.page(path='/events/2/?bs=5&offset=25')
        self.assertIn('aria-label="Places taken" aria-valuenow="0"', html)
        self.assertIn('<strong>0/100</strong>', html)
        self.people = [attendee(n) for n in range(3)]
        html = self.page(path='/events/2/?bs=5&offset=25')
        # The view shows at least 10% once anyone is going.
        self.assertIn('aria-valuenow="10"', html)
        self.assertIn('style="width: 10%"', html)
        self.assertIn('<strong>3/100</strong>', html)

    # RSVP ------------------------------------------------------------------------------

    def test_guest_is_asked_to_sign_in(self):
        rsvp = self.rsvp_html(self.page())
        self.assertIn('Sign in to reserve your place in this event!', rsvp)
        self.assertIn('onclick="authSignin();">Sign in or register to attend</button>', rsvp)
        self.assertNotIn('<form', rsvp)

    def test_member_can_say_yes(self):
        rsvp = self.rsvp_html(self.page(member=True))
        self.assertIn('<form method="POST" action="/events/2/rsvp/">', rsvp)
        self.assertIn('name="csrfmiddlewaretoken"', rsvp)
        self.assertIn('<input type="hidden" name="rsvp" value="yes">', rsvp)
        self.assertIn('>Yes, I\'m attending!</button>', rsvp)

    def test_attending_member_can_say_no(self):
        self.event['meta']['flags']['attending'] = True
        rsvp = self.rsvp_html(self.page(member=True))
        self.assertIn('You are attending this event.', rsvp)
        self.assertIn('<input type="hidden" name="rsvp" value="no">', rsvp)
        self.assertIn('id="rsvp_no" type="submit" class="btn mw-btn">Can\'t make it</button>', rsvp)

    def test_a_full_event(self):
        self.set(rsvpLimit=2)
        self.people = [attendee(1), attendee(2)]
        rsvp = self.rsvp_html(self.page(member=True))
        self.assertIn('This event is full.', rsvp)
        self.assertNotIn('<form', rsvp)

    def test_a_past_event(self):
        self.set(when='2019-04-27T09:45:00Z')
        self.people = [attendee(1)]
        rsvp = self.rsvp_html(self.page(member=True))
        self.assertIn('Follow this forum to be notified whenever a new event is added.', rsvp)
        self.assertNotIn('<form', rsvp)
        # Past and nobody going: no RSVP bar at all, as on Bootstrap 3.
        self.people = []
        self.assertNotIn('mw-event-actions', self.page(member=True))

    # The metabar -----------------------------------------------------------------------

    def test_metabar(self):
        guest = self.page()
        self.assertIn('data-bs-target="#modal-signin">', guest)
        self.assertNotIn('Download Attendees CSV', guest)
        self.event['meta']['permissions'].update(update=True, owner=True)
        member = self.page(member=True)
        self.assertIn('<a id="edit-event" href="/events/2/edit/"', member)
        self.assertIn('<a id="csv-event" href="/events/2/csv/">Download Attendees CSV</a>', member)
        self.assertIn('data-item-type="event" data-item-id="2"', member)
        self.assertIn('<input type="hidden" name="type" value="event">', member)
        self.assertIn('js/bs5/comments.js', member)

    def test_bootstrap_3_page_is_unchanged(self):
        html = self.page(path='/events/2/?bs=3')
        self.assertNotIn('bs5.min.css', html)
        self.assertIn('sprite sprite-calendar', html)
        self.assertIn('js/eventMap.js', html)

    def test_event_row_is_unchanged_by_the_header(self):
        # The header's place is .mw-event-place, never the row pill's .mw-event-where.
        self.assertNotIn('mw-event-where', PARTIAL.read_text())
        row = engines['bs5'].get_template('block_event.html').render(
            {'item': Event.from_summary(copy.deepcopy(self.event)), 'site': make_site()})
        self.assertIn('<span class="mw-event-where"', row)
