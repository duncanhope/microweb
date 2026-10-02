"""The error pages fetch the Site (and, for 403 and 404, the visitor) to
dress the page. When that fetch failed in a way build_error_view_data did
not expect, the error page itself raised, and the visitor got the server's
bare 500 instead of the page: an unreachable API on a custom domain whose
address was not cached, an expired token's 401, or an answer that was not
JSON. Each now falls back to the plain page."""
import json
from unittest import mock

import requests
from django.test import RequestFactory, SimpleTestCase

from core import views
from core.api.resources import Site, WhoAmI
from core.tests.test_edit_reason import load

SITE_URL = 'https://lfgss.microcosm.app/api/v1/site'
WHOAMI_URL = 'https://lfgss.microcosm.app/api/v1/whoami'


def answer(url, status=200, body=None, text=None):
    response = requests.Response()
    response.url = url
    response.status_code = status
    response._content = (text if text is not None else json.dumps(body)).encode()
    return response


def site_answer():
    return answer(SITE_URL, body={'error': None, 'data': load('site.json')})


def signed_in(path='/no-such-page/'):
    request = RequestFactory().get(path, HTTP_HOST='www.lfgss.com')
    request.COOKIES['access_token'] = 'expired'
    return request


class ErrorPagesFailSafeTests(SimpleTestCase):

    def patched(self, responses):
        return [mock.patch.object(Site, 'build_request', return_value=(SITE_URL, {}, {})),
                mock.patch.object(WhoAmI, 'build_request', return_value=(WHOAMI_URL, {}, {})),
                mock.patch.object(views.fetch, 'map', return_value=responses)]

    def run_with(self, responses, view, request):
        patches = self.patched(responses)
        for p in patches:
            p.start()
        try:
            return view(request)
        finally:
            for p in patches:
                p.stop()

    def test_an_unreachable_api_on_an_uncached_custom_domain(self):
        failure = requests.ConnectionError('made-up refusal')
        with mock.patch.object(Site, 'build_request', side_effect=failure):
            for view, status in ((views.ErrorView.not_found, 404), (views.ErrorView.forbidden, 403),
                                 (views.ErrorView.server_error, 500)):
                with self.subTest(status=status):
                    self.assertEqual(view(signed_in()).status_code, status)

    def test_an_expired_token_still_shows_the_site(self):
        expired = answer(WHOAMI_URL, 401, {'error': 'Bad access token', 'data': None})
        with self.assertLogs('core.views', 'WARNING'):
            response = self.run_with([expired, site_answer()], views.ErrorView.not_found, signed_in())
        self.assertEqual(response.status_code, 404)
        html = response.content.decode()
        self.assertIn('Not Found', html)
        self.assertIn('<title>Not Found | Middle Earth', html)

    def test_an_answer_that_is_not_json(self):
        broken = answer(SITE_URL, 502, text='<html>Bad gateway</html>')
        with self.assertLogs('core.views', 'WARNING'):
            response = self.run_with([broken], views.ErrorView.server_error, RequestFactory().get('/'))
        self.assertEqual(response.status_code, 500)
