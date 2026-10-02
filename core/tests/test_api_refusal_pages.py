"""Two forms read the API's answer straight from requests and, when the
API refused, returned an empty 400: an RSVP, and ignoring or unignoring an
item. Each refusal now shows the error page its status calls for, as every
other refusal does. Every event, person and answer here is made up."""
import json
from unittest import mock

import requests
from django.test import SimpleTestCase

from core.api.resources import Event, Ignored
from core.tests.helpers import SITE_URL, WHOAMI_URL, load, request
from events import views as event_views
from ignored import views as ignored_views


def refusal(status, error):
    response = requests.Response()
    response.url = 'https://dev1.microcosm.app/api/v1/made-up'
    response.status_code = status
    response._content = json.dumps({'error': error, 'data': None}).encode()
    return response


class ApiRefusalPageTests(SimpleTestCase):

    def run_view(self, views, view, req, *args):
        responses = {SITE_URL: load('site.json'), WHOAMI_URL: load('whoami.json')}
        with mock.patch.object(views.fetch, 'map', return_value=[]), \
                mock.patch.object(views, 'response_list_to_dict', return_value=responses):
            return view(req, *args)

    def setUp(self):
        patch = mock.patch('core.views.build_error_view_data', return_value={})
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_refused_rsvp(self):
        for status, page in ((403, 'Not permitted'), (400, 'Bad Request')):
            with self.subTest(status=status), \
                    mock.patch.object(Event, 'rsvp_api', return_value=refusal(status, 'Made-up refusal')):
                response = self.run_view(event_views, event_views.rsvp,
                                         request('/events/2/rsvp/', 'post', {'rsvp': 'yes'}), '2')
                self.assertEqual(response.status_code, status)
                self.assertIn(page, response.content.decode())

    def test_a_refused_ignore(self):
        for delete in ('', '1'):
            api = 'delete_api' if delete else 'add_api'
            with self.subTest(delete=bool(delete)), \
                    mock.patch.object(Ignored, api, return_value=refusal(404, 'Made-up refusal')), \
                    self.assertLogs('ignored.views', 'ERROR'):
                response = ignored_views.ignore(request('/ignored/', 'post', {
                    'item_type': 'conversation', 'item_id': '1', 'delete': delete}))
                self.assertEqual(response.status_code, 404)
                self.assertIn('Not Found', response.content.decode())
