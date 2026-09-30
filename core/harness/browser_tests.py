"""Playwright interaction checks, replayed from the harness recording.

Run with `python manage.py test --tag browser` after one
`python manage.py shoot --record`. A plain `manage.py test` never imports
this module (see core/test_runner.py). Each family PR adds its checks as
BrowserTestCase subclasses in a `*browser_tests.py` module.

Results land in `.harness/checks.json`, which `shoot` shows in the summary.
"""
import json
import os
from datetime import datetime
from unittest import SkipTest
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag

from core.harness import browser, manifest, recorder
from core.middleware.context import COLOR_MODE_COOKIE

REPO_ROOT = os.path.dirname(settings.PROJECT_ROOT)
HARNESS_DIR = os.path.join(REPO_ROOT, '.harness')
CHECKS_PATH = os.path.join(HARNESS_DIR, 'checks.json')


def bs5(path):
    """path, asking for Bootstrap 5."""
    return path + ('&' if '?' in path else '?') + 'bs=5'


@tag('browser')
@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class BrowserTestCase(StaticLiveServerTestCase):
    """A live server replaying recorded API calls, frozen at the recording's
    time, and a Chromium whose Site hosts are routed to it."""

    databases = set()
    fixtures_dir = os.environ.get('HARNESS_FIXTURES', os.path.join(HARNESS_DIR, 'fixtures'))

    @classmethod
    def setUpClass(cls):
        meta_path = os.path.join(cls.fixtures_dir, 'meta.json')
        if not os.path.exists(meta_path):
            raise SkipTest('No harness recording in %s. Run: python manage.py shoot --record' % cls.fixtures_dir)
        try:
            import freezegun
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise SkipTest('Browser checks need: pip install -r requirements-dev.txt')
        with open(meta_path) as f:
            cls.meta = json.load(f)
        mode = os.environ.get('HARNESS_MODE', recorder.REPLAY)
        cls.frozen = datetime.fromisoformat(cls.meta['recorded_at'].replace('Z', '+00:00'))
        cls._recorder = recorder.install(cls.fixtures_dir, mode, cls.meta['session'])
        # real_asyncio keeps Playwright's event loop on real time.
        cls._freezer = freezegun.freeze_time(cls.meta['recorded_at'], tick=False, real_asyncio=True)
        cls._freezer.start()
        cls.results = {}
        try:
            super().setUpClass()
            cls.store = browser.BrowserStore(os.path.join(cls.fixtures_dir, 'browser.har'), mode, cls.meta['session'])
            cls.playwright = sync_playwright().start()
            cls.chromium = cls.playwright.chromium.launch(args=browser.LAUNCH_ARGS)
        except Exception:
            cls._stop_harness()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            cls.chromium.close()
            cls.playwright.stop()
            cls.store.save()
            super().tearDownClass()
        finally:
            cls._stop_harness()
            cls._write_results()

    @classmethod
    def _stop_harness(cls):
        cls._freezer.stop()
        cls._recorder.uninstall()

    @classmethod
    def _write_results(cls):
        if not cls.results:
            return
        checks = {'results': {}}
        if os.path.exists(CHECKS_PATH):
            with open(CHECKS_PATH) as f:
                checks = json.load(f)
        checks['results'].update(cls.results)
        checks['ran_at'] = datetime.now().replace(microsecond=0).isoformat()
        os.makedirs(HARNESS_DIR, exist_ok=True)
        with open(CHECKS_PATH, 'w') as f:
            json.dump(checks, f, indent=1)

    def run(self, result=None):
        result = result or self.defaultTestResult()
        before = [len(result.failures), len(result.errors), len(result.skipped)]
        super().run(result)
        after = [len(result.failures), len(result.errors), len(result.skipped)]
        outcome = 'pass'
        for name, b, a in zip(('fail', 'error', 'skip'), before, after):
            if a > b:
                outcome = name
        type(self).results[self.id()] = outcome
        return result

    def new_page(self, width=1280, height=900, color_scheme='light', signed_in=False):
        """A page in a fresh context: Site hosts routed here, clock frozen."""
        context = self.chromium.new_context(
            viewport={'width': width, 'height': height}, device_scale_factor=1, color_scheme=color_scheme,
            reduced_motion='reduce', user_agent=browser.user_agent(self.chromium.version))
        self.addCleanup(context.close)
        context.clock.set_fixed_time(self.frozen)
        if signed_in:
            token = os.environ.get('HARNESS_TOKEN')
            if not token:
                self.skipTest('HARNESS_TOKEN is not set; skipping a signed-in check.')
            context.add_cookies([{'name': 'access_token', 'value': token, 'url': 'https://%s/' % host}
                                 for host in manifest.site_hosts()])
        router = browser.Router({h: self.server_thread.port for h in manifest.site_hosts()}, self.store)
        context.route('**/*', browser.sync_handler(router))
        return context.new_page()

    def open_bs5(self, path, host=manifest.LFGSS, width=1280, signed_in=False, color_mode=None, status=200,
                 by_cookie=False):
        """Open a page with ?bs=5, or the bs cookie when by_cookie, and fail the
        check on any script error."""
        page = self.new_page(width=width, signed_in=signed_in)
        cookies = [{'name': name, 'value': value, 'url': 'https://%s/' % host}
                   for name, value in ((COLOR_MODE_COOKIE, color_mode), ('bs', '5' if by_cookie else None)) if value]
        if cookies:
            page.context.add_cookies(cookies)
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        # Off-site requests the recording lacks are aborted by design; only
        # script errors count.
        page.on('console', lambda msg: errors.append(msg.text)
                if msg.type == 'error' and not msg.text.startswith('Failed to load resource') else None)
        response = page.goto('https://%s%s' % (host, path if by_cookie else bs5(path)), wait_until='load')
        self.assertEqual(response.status, status)
        page.wait_for_function('() => window.bootstrap')
        self.addCleanup(lambda: self.assertEqual(errors, [], 'script errors on the page'))
        return page

    def submit(self, page, click, action):
        """Run click, which posts a form to the path `action`, and wait for the
        page its redirect lands on. The harness answers a redirect with a
        stand-in page at `action` that moves on by itself (core/harness/browser.py)."""
        with page.expect_navigation(url=lambda url: urlsplit(url).path == action, wait_until='commit'):
            click()
        # A redirect can take more than one stand-in page (Django's added slash).
        page.wait_for_function('() => document.readyState === "complete"'
                               ' && !document.querySelector("meta[name=harness-redirect]")')

    def snap(self, page, name):
        """Keep a screenshot of the check in .harness/checks/ for review."""
        path = os.path.join(HARNESS_DIR, 'checks', '%s.png' % name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        page.screenshot(path=path)
        return path


class PageJumpTests(BrowserTestCase):

    def test_page_jump_navigates_to_offset(self):
        page = self.new_page()
        page.goto('https://%s/microcosms/509/' % manifest.LFGSS, wait_until='load')
        form = page.locator('.pagination-alt form[name=paginationByOffset]').first
        limit = int(form.get_attribute('data-limit'))
        self.assertGreaterEqual(int(form.get_attribute('data-max')), 3)
        field = form.locator('input[type=text]')
        field.fill('3')
        with page.expect_navigation(wait_until='load'):
            field.blur()  # base.js submits the jump form on blur
        self.snap(page, 'page-jump')
        url = urlsplit(page.url)
        self.assertEqual(url.path, '/microcosms/509/')
        self.assertEqual(parse_qs(url.query).get('offset'), [str(limit * 2)])
        self.assertEqual(page.locator('.pagination li.active a').first.inner_text().strip(), '3')
