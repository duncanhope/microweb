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


class EventInviteTests(SimpleTestCase):
    """Invites on the event form. Both trees post everyone listed in the
    invite box as comma-separated profile ids, which on the edit form
    includes everyone who already has an RSVP (they are listed, and cannot be
    removed). Only the people added are invited, as maybe."""

    def request(self, path, data):
        request = RequestFactory().post(path, data, HTTP_HOST=HOST)
        request.access_token = 'token'
        request.whoami_url = WHOAMI_URL
        request.site_url = SITE_URL
        request.view_requests = [views.fetch.get(SITE_URL), views.fetch.get(WHOAMI_URL)]
        request.color_mode = 'auto'
        return request

    def post(self, view, path, api, **fields):
        """Post the form to view, and return the RSVPs it sent as (url, payload)."""
        data = {'microcosmId': '1', 'title': 'Generated Event', 'when': '2026-10-10T19:00:00Z', 'duration': '120',
                'tz': 'Europe/London', 'where': '', 'rsvpLimit': '', 'invite': '', 'inviteObject': '',
                'firstcomment': ''}
        data.update(fields)
        event = load('event_with_comment.json')
        event['id'] = EVENT_ID
        saved = Mock(status_code=200)
        saved.json.return_value = {'error': None, 'data': event}
        with patch('requests.get', side_effect=api.get), \
                patch('requests.post', return_value=saved) as post, \
                patch('requests.put', return_value=Mock(status_code=200)) as put:
            response = view(self.request(path, data), str(EVENT_ID if view is views.edit else 1))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/events/%d/' % EVENT_ID)
        self.assertEqual(post.call_count, 1)
        return [(call.args[0], json.loads(call.kwargs['data'])) for call in put.call_args_list]

    def edit(self, api, invite):
        return self.post(views.edit, '/events/4488/edit/', api, id=str(EVENT_ID), editReason='Invites',
                         invite=invite)

    def test_the_create_form_invites_everyone_listed(self):
        rsvps = self.post(views.create, '/microcosms/1/create/event/', FakeAPI(going=0, invited=0),
                          invite='201,202')
        self.assertEqual(rsvps, [(ATTENDEES_URL, [{'rsvp': 'maybe', 'profileId': 201},
                                                  {'rsvp': 'maybe', 'profileId': 202}])])

    def test_the_edit_form_invites_the_people_added(self):
        # rider0 and rider1 (100, 101) are going, rider2 (102) is invited; 201 and 202 are new.
        api = FakeAPI(going=2, invited=1)
        rsvps = self.edit(api, '100,101,102,201,202')
        self.assertEqual(rsvps, [(ATTENDEES_URL, [{'rsvp': 'maybe', 'profileId': 201},
                                                  {'rsvp': 'maybe', 'profileId': 202}])])

    def test_the_edit_form_leaves_everyone_with_an_rsvp_alone(self):
        # Someone who said no stays a no: they are not invited again.
        api = FakeAPI(going=1, invited=1)
        api.attendees.append(attendee(2, 'no'))
        self.assertEqual(self.edit(api, '100,101,102'), [])

    def test_the_edit_form_checks_every_page_of_attendees(self):
        api = FakeAPI(going=300, invited=0)
        rsvps = self.edit(api, '100,399,450')
        self.assertEqual(rsvps, [(ATTENDEES_URL, [{'rsvp': 'maybe', 'profileId': 450}])])

    def test_the_edit_form_without_invites_sends_none(self):
        api = FakeAPI(going=2, invited=0)
        self.assertEqual(self.edit(api, ''), [])
        # Nor asks for the attendees.
        self.assertEqual(api.attendee_calls(), [])

    # The Bootstrap 3 form lists the people chosen again after an error -----------

    def bs3_script(self, request):
        with patch('requests.get', side_effect=FakeAPI(going=1, invited=0).get):
            response = (views.edit(request, str(EVENT_ID)) if '/edit/' in request.path
                        else views.create(request, '1'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        return html[html.index('//    Invite object   //'):]

    def test_the_bootstrap_3_form_lists_the_people_chosen_after_an_error(self):
        chosen = [{'id': 201, 'profileName': 'o\'neil</script>', 'avatar': ''}]
        # No reason for the edit, so the form comes back.
        request = self.request('/events/4488/edit/?bs=3', {
            'id': str(EVENT_ID), 'microcosmId': '1', 'title': 'Generated Event', 'tz': 'Europe/London',
            'invite': '100,201', 'inviteObject': json.dumps(chosen)})
        script = self.bs3_script(request)
        self.assertIn("window.form_invitees = JSON.parse('[{\\u0022id\\u0022: 201, \\u0022profileName\\u0022: "
                      "\\u0022o\\u0027neil\\u003C/script\\u003E\\u0022", script)
        self.assertNotIn('</script>\\', script)

    def test_the_bootstrap_3_edit_form_lists_everyone_with_an_rsvp(self):
        request = RequestFactory().get('/events/4488/edit/?bs=3', HTTP_HOST=HOST)
        for name, value in vars(self.request('/', {})).items():
            if name in ('access_token', 'whoami_url', 'site_url', 'view_requests', 'color_mode'):
                setattr(request, name, value)
        script = self.bs3_script(request)
        self.assertIn("window.form_invitees = JSON.parse('[{\\u0022id\\u0022: 100, \\u0022profileName\\u0022: "
                      "\\u0022rider0\\u0022", script)

    def test_the_bootstrap_3_create_form_starts_with_nobody(self):
        request = RequestFactory().get('/microcosms/1/create/event/?bs=3', HTTP_HOST=HOST)
        for name, value in vars(self.request('/', {})).items():
            if name in ('access_token', 'whoami_url', 'site_url', 'view_requests', 'color_mode'):
                setattr(request, name, value)
        self.assertNotIn('window.form_invitees', self.bs3_script(request).split('</script>')[0])
