"""The RSVP controls on the event page, in both template trees and in both
headers: event_header_large.html (an event with a place on the map) and
event_header_small.html (the rest). The Yes and No controls show only when
the viewer can RSVP; otherwise the header says RSVP is closed."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Event
from events import views

DATA = Path(__file__).resolve().parent / 'data'
EVENT_URL, ATTENDEES_URL, SITE_URL, WHOAMI_URL = 'event', 'attendees', 'site', 'whoami'
RSVP_ACTION = 'action="/events/2/rsvp/"'
CLOSED = 'RSVP is closed.'


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


class EventRsvpTests(SimpleTestCase):

    def setUp(self):
        self.event = load('event_with_comment.json')
        start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=10)
        self.event.update(when=start.strftime('%Y-%m-%dT%H:%M:%SZ'), duration=120, rsvpLimit=0)
        self.event.pop('rsvpSpaces', None)
        # A signed-in member of the forum: the API grants create on the event,
        # which is what it checks before it takes an RSVP.
        self.event['meta']['permissions'].update(create=True, guest=False)

    def page(self, bs, large, member=True):
        self.event.pop('lat', None)
        if large:
            self.event.update(where='IKEA Croydon', lat=51.38, lon=-0.12, north=51.39, west=-0.13, south=51.37,
                              east=-0.11)
        request = RequestFactory().get('/events/2/?bs=%d' % bs)
        request.access_token = 'token' if member else None
        request.whoami_url = WHOAMI_URL if member else ''
        request.site_url = SITE_URL
        request.view_requests = []
        request.color_mode = 'auto'
        responses = {
            EVENT_URL: self.event,
            ATTENDEES_URL: {'attendees': {'total': 0, 'limit': 250, 'offset': 0, 'maxOffset': 0, 'totalPages': 1,
                                          'page': 1, 'links': [], 'type': '', 'items': []},
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

    def pages(self, **kwargs):
        """The page from each tree, with each header."""
        return [(dict(bs=bs, large=large), self.page(bs, large, **kwargs)) for bs in (3, 5) for large in (False, True)]

    def test_an_open_event_offers_yes(self):
        for variant, html in self.pages():
            with self.subTest(**variant):
                self.assertIn(RSVP_ACTION, html)
                self.assertIn('attending!', html)
                self.assertNotIn(CLOSED, html)

    def test_a_closed_event_offers_no_rsvp(self):
        self.event['meta']['flags']['open'] = False
        for variant, html in self.pages():
            with self.subTest(**variant):
                self.assertNotIn(RSVP_ACTION, html)
                self.assertIn(CLOSED, html)

    def test_an_attendee_of_a_closed_event_cannot_withdraw(self):
        self.event['meta']['flags'].update(open=False, attending=True)
        for variant, html in self.pages():
            with self.subTest(**variant):
                self.assertNotIn(RSVP_ACTION, html)
                self.assertNotIn("Can't make it", html)
                self.assertIn('You are attending this event.', html)
                self.assertIn(CLOSED, html)

    def test_a_member_the_api_would_refuse_gets_no_rsvp(self):
        self.event['meta']['permissions']['create'] = False
        for variant, html in self.pages():
            with self.subTest(**variant):
                self.assertNotIn(RSVP_ACTION, html)
                self.assertIn(CLOSED, html)

    def test_a_cancelled_event_offers_no_rsvp(self):
        self.event['status'] = 'cancelled'
        for variant, html in self.pages():
            with self.subTest(**variant):
                self.assertNotIn(RSVP_ACTION, html)
                self.assertIn(CLOSED, html)

    def test_a_guest_is_still_asked_to_sign_in(self):
        self.event['meta']['flags']['open'] = False
        for variant, html in self.pages(member=False):
            with self.subTest(**variant):
                self.assertIn('Sign in to reserve your place in this event!', html)
                self.assertNotIn(CLOSED, html)


class EventRsvpOpenTests(SimpleTestCase):

    def event(self, open=True, create=True, status='upcoming'):
        data = load('event_with_comment.json')
        data['status'] = status
        data['meta']['flags']['open'] = open
        data['meta']['permissions']['create'] = create
        return Event.from_api_response(data)

    def test_rsvp_open(self):
        self.assertTrue(self.event().rsvp_open)
        self.assertTrue(self.event(status='proposed').rsvp_open)
        self.assertFalse(self.event(open=False).rsvp_open)
        self.assertFalse(self.event(create=False).rsvp_open)
        self.assertFalse(self.event(status='cancelled').rsvp_open)
