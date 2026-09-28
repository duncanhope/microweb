from unittest.mock import patch

from django.test import RequestFactory
from django.test import SimpleTestCase

from core.middleware.context import ContextMiddleware


@patch('core.middleware.context.Site.build_request',
       return_value=('https://lfgss.microcosm.app/api/v1/site', {}, {}))
class ColorModeCookieTests(SimpleTestCase):
    """ContextMiddleware reads the color_mode cookie into request.color_mode."""

    def process(self, path='/', **cookies):
        request = RequestFactory().get(path, HTTP_HOST='lfgss.microcosm.app')
        request.COOKIES.update(cookies)
        self.assertIsNone(ContextMiddleware(lambda r: None).process_request(request))
        return request

    def test_each_color_mode(self, _):
        for value in ('light', 'dark', 'auto'):
            with self.subTest(value=value):
                self.assertEqual(self.process(color_mode=value).color_mode, value)

    def test_missing_cookie_is_auto(self, _):
        self.assertEqual(self.process().color_mode, 'auto')

    def test_anything_else_is_auto(self, _):
        for value in ('', 'Dark', 'high-contrast', 'dark; path=/'):
            with self.subTest(value=value):
                self.assertEqual(self.process(color_mode=value).color_mode, 'auto')

    def test_readiness_check_is_untouched(self, build_request):
        request = self.process('/health/ready', color_mode='dark')
        self.assertFalse(hasattr(request, 'color_mode'))
        build_request.assert_not_called()
