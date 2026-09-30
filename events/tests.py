import json
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import build_url
from events import views

DATA = Path(__file__).resolve().parent.parent / 'core' / 'tests' / 'data'
HOST = 'lfgss.microcosm.app'
EVENT_ID = 4488
EVENT_URL = build_url(HOST, ['events', EVENT_ID])
ATTENDEES_URL = build_url(HOST, ['events', EVENT_ID, 'attendees'])
SITE_URL = build_url(HOST, ['site'])
WHOAMI_URL = build_url(HOST, ['whoami'])


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


def attendee(n, rsvp):
    profile = {'id': 100 + n, 'siteId': 1, 'userId': 100 + n, 'profileName': 'rider%d' % n, 'visible': True,
               'avatar': '', 'meta': {'flags': {}, 'links': []}}
    return {'profileId': 100 + n, 'profile': profile, 'rsvp': rsvp, 'rsvpdOn': '2026-09-01T10:00:00Z',
            'meta': {'created': '2026-09-01T10:00:00Z', 'flags': {}, 'links': []}}


class FakeAPI(object):
    """Answers GETs the way the Microcosm API does: attendees come a page at a
    time, 25 unless the request asks for a larger limit (a multiple of 5, at
    most 250)."""

    def __init__(self, going, invited):
        self.attendees = [attendee(n, 'yes') for n in range(going)] + \
                         [attendee(going + n, 'maybe') for n in range(invited)]
        self.calls = []

    def page(self, params):
        limit, offset, total = int(params.get('limit', 25)), int(params.get('offset', 0)), len(self.attendees)
        if limit % 5 or limit > 250:
            return {'error': ['limit (%d) is not allowed' % limit], 'data': None}
        return {'error': None, 'data': {
            'attendees': {'total': total, 'limit': limit, 'offset': offset,
                          'maxOffset': ((total - 1) // limit) * limit, 'totalPages': (total - 1) // limit + 1,
                          'page': offset // limit + 1, 'links': [], 'type': 'attendee',
                          'items': self.attendees[offset:offset + limit]},
            'meta': {'flags': {}, 'links': []}}}

    def get(self, url, params=None, headers=None, **kwargs):
        params = dict(params or {})
        self.calls.append((url, params))
        if url == ATTENDEES_URL:
            body = self.page(params)
        else:
            data = {EVENT_URL: load('event_with_comment.json'), SITE_URL: load('site.json'),
                    WHOAMI_URL: load('whoami.json')}[url]
            body = {'error': None, 'data': data}
        response = Mock(history=[], status_code=200 if body['data'] else 400)
        response.url = url + ('?' + urlencode(params) if params else '')
        response.json.return_value = body
        return response

    def attendee_calls(self):
        return [params for url, params in self.calls if url == ATTENDEES_URL]


class EventAttendeesTests(SimpleTestCase):
    """The event page and the event form list every attendee, not the API's
    first page of 25."""

    def request(self, path):
        request = RequestFactory().get(path, HTTP_HOST=HOST)
        request.access_token = 'token'
        request.whoami_url = WHOAMI_URL
        request.site_url = SITE_URL
        request.view_requests = [views.fetch.get(SITE_URL), views.fetch.get(WHOAMI_URL)]
        request.color_mode = 'auto'
        return request

    def view_data(self, view, api, path):
        with patch('requests.get', side_effect=api.get), \
                patch.object(views, 'render', return_value=HttpResponse()) as render:
            view(self.request(path), str(EVENT_ID))
        self.assertEqual(render.call_count, 1)
        return render.call_args.args[2]

    def test_the_event_page_lists_all_26_attendees(self):
        api = FakeAPI(going=21, invited=5)
        data = self.view_data(views.single, api, '/events/4488/')
        self.assertEqual(len(data['attendees'].items.items), 26)
        self.assertEqual(data['rsvp_num_attending'], 21)
        self.assertEqual(data['rsvp_num_invited'], 5)
        # One request for the attendees, in the page's batch.
        self.assertEqual(api.attendee_calls(), [{'limit': 250}])

    def test_the_event_page_fetches_further_pages_past_the_apis_largest_limit(self):
        api = FakeAPI(going=250, invited=270)
        data = self.view_data(views.single, api, '/events/4488/')
        self.assertEqual(len(data['attendees'].items.items), 520)
        self.assertEqual(len({a.profile_id for a in data['attendees'].items.items}), 520)
        self.assertEqual(data['rsvp_num_attending'], 250)
        self.assertEqual(data['rsvp_num_invited'], 270)
        self.assertEqual(sorted(p.get('offset', 0) for p in api.attendee_calls()), [0, 250, 500])

    def test_the_event_form_invites_every_attendee(self):
        api = FakeAPI(going=21, invited=5)
        data = self.view_data(views.edit, api, '/events/4488/edit/')
        invitees = json.loads(data['attendees_json'])
        self.assertEqual(len(invitees), 26)
        self.assertEqual(invitees[-1]['profileName'], 'rider25')
