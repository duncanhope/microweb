"""Two 404s were empty pages: an unknown /about/ document, and a host the
API cannot resolve (a mistyped custom domain). Both now show the Not Found
page, in either design. A bare IP address in the Host header is still
refused with an empty 404, since only scanners send one."""
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from core.api.exceptions import APIException
from core.middleware.context import ContextMiddleware
from core.views import LegalView


class Empty404Tests(SimpleTestCase):

    def test_an_unknown_about_page(self):
        for bs in (3, 5):
            with self.subTest(bs=bs), mock.patch('core.views.build_error_view_data', return_value={}):
                request = RequestFactory().get('/about/nonsense/?bs=%d' % bs)
                response = LegalView.single(request, 'nonsense')
                self.assertEqual(response.status_code, 404)
                self.assertIn('Not Found', response.content.decode())

    def test_a_host_the_api_cannot_resolve(self):
        refusal = APIException('Error resolving CNAME forum.example.org', 404)
        for bs in (3, 5):
            with self.subTest(bs=bs), mock.patch('core.middleware.context.Site.build_request', side_effect=refusal), \
                    mock.patch('core.views.build_error_view_data') as lookup:
                request = RequestFactory().get('/?bs=%d' % bs, HTTP_HOST='forum.example.org')
                response = ContextMiddleware(lambda r: None).process_request(request)
                self.assertEqual(response.status_code, 404)
                self.assertIn('Not Found', response.content.decode())
                # The host is already known to be unresolvable: no second lookup.
                lookup.assert_not_called()

    def test_an_ip_address_host_is_still_refused_bare(self):
        refusal = APIException('Error resolving CNAME 192.0.2.1', 404)
        with mock.patch('core.middleware.context.Site.build_request', side_effect=refusal):
            request = RequestFactory().get('/', HTTP_HOST='192.0.2.1')
            response = ContextMiddleware(lambda r: None).process_request(request)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b'')
