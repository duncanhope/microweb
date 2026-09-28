import shutil
import tempfile
from pathlib import Path

from django.test import RequestFactory
from django.test import SimpleTestCase
from django.test import override_settings

from core.framework import COOKIE
from core.framework import get_template
from core.framework import render


def _templates(bs3_dir, bs5_dir):
    options = {'context_processors': ['django.template.context_processors.request']}
    return [
        {'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [bs3_dir], 'OPTIONS': options},
        {'NAME': 'bs5', 'BACKEND': 'django.template.backends.django.DjangoTemplates',
         'DIRS': [bs5_dir, bs3_dir], 'OPTIONS': options},
    ]


class FrameworkTests(SimpleTestCase):
    """core.framework picks Bootstrap 5 only on request and only for migrated pages."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(tempfile.mkdtemp())
        bs3, bs5 = cls.root / 'bs3', cls.root / 'bs5'
        bs3.mkdir()
        bs5.mkdir()
        (bs3 / 'migrated.html').write_text('bs3 page {% include "shared.html" %}{% include "other.html" %}')
        (bs3 / 'unmigrated.html').write_text('bs3 unmigrated')
        (bs3 / 'shared.html').write_text('bs3 shared')
        (bs3 / 'other.html').write_text('bs3 other')
        (bs5 / 'migrated.html').write_text('bs5 page {% include "shared.html" %}{% include "other.html" %}')
        (bs5 / 'shared.html').write_text('bs5 shared')
        cls.settings_override = override_settings(
            TEMPLATES=_templates(str(bs3), str(bs5)), BS5_TEMPLATE_DIR=str(bs5))
        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.settings_override.disable()
        shutil.rmtree(cls.root)
        super().tearDownClass()

    def setUp(self):
        self.factory = RequestFactory()

    def get(self, query='', cookie=None):
        request = self.factory.get('/' + query)
        if cookie is not None:
            request.COOKIES[COOKIE] = cookie
        return request

    def test_no_preference_renders_bootstrap_3(self):
        response = render(self.get(), 'migrated.html')
        self.assertEqual(response.content, b'bs3 page bs3 sharedbs3 other')

    def test_query_renders_bootstrap_5_for_a_migrated_page(self):
        response = render(self.get('?bs=5'), 'migrated.html')
        self.assertTrue(response.content.startswith(b'bs5 page'))

    def test_cookie_renders_bootstrap_5_for_a_migrated_page(self):
        response = render(self.get(cookie='5'), 'migrated.html')
        self.assertTrue(response.content.startswith(b'bs5 page'))

    def test_unmigrated_page_stays_bootstrap_3_with_the_cookie(self):
        response = render(self.get(cookie='5'), 'unmigrated.html')
        self.assertEqual(response.content, b'bs3 unmigrated')

    def test_query_bs3_overrides_a_bs5_cookie(self):
        response = render(self.get('?bs=3', cookie='5'), 'migrated.html')
        self.assertTrue(response.content.startswith(b'bs3 page'))

    def test_includes_prefer_bootstrap_5_and_fall_back_to_bootstrap_3(self):
        response = render(self.get('?bs=5'), 'migrated.html')
        self.assertEqual(response.content, b'bs5 page bs5 sharedbs3 other')

    def test_query_sets_a_lax_http_only_cookie(self):
        for choice in ('3', '5'):
            cookie = render(self.get('?bs=' + choice), 'migrated.html').cookies[COOKIE]
            self.assertEqual(cookie.value, choice)
            self.assertEqual(cookie['samesite'], 'Lax')
            self.assertTrue(cookie['httponly'])

    def test_no_or_unknown_query_sets_no_cookie(self):
        self.assertNotIn(COOKIE, render(self.get(), 'migrated.html').cookies)
        self.assertNotIn(COOKIE, render(self.get('?bs=4'), 'migrated.html').cookies)

    def test_get_template_follows_the_same_choice(self):
        request = self.get(cookie='5')
        self.assertTrue(get_template(request, 'migrated.html').render({}, request).startswith('bs5 page'))
        self.assertEqual(get_template(self.get(), 'migrated.html').render({}, self.get()),
                         'bs3 page bs3 sharedbs3 other')
