"""Logging an API failure failed or said nothing. An APIException without
a status code (the API answering with no data) raised a TypeError when
turned into text, which any log line or error page holding it then
raised; and the redirect view logged the APIException class rather than
the exception it caught."""
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from core.api.exceptions import APIException
from core.api.resources import Redirect, Site
from redirect import views


class ApiExceptionLoggingTests(SimpleTestCase):

    def test_an_exception_without_a_status_reads_as_text(self):
        self.assertEqual(str(APIException('No data returned at: made-up')), 'No data returned at: made-up')
        self.assertEqual(str(APIException('Made-up refusal', 403)), 'HTTP status: 403: Made-up refusal')

    def test_the_redirect_view_logs_the_exception_it_caught(self):
        request = RequestFactory().get('/old/forum/page/', HTTP_HOST='forum.example.org')
        request.access_token = None
        with mock.patch.object(Site, 'resolve_cname', side_effect=APIException('Made-up lookup failure', 404)), \
                mock.patch.object(Redirect, 'get', side_effect=APIException('Made-up', 404)), \
                mock.patch('core.views.build_error_view_data', return_value={}), \
                self.assertLogs('redirect.views', 'ERROR') as logs:
            response = views.redirect_or_404(request)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(logs.output, ['ERROR:redirect.views:HTTP status: 404: Made-up lookup failure'])
