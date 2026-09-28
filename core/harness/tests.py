import json
import os
import shutil
import tempfile
from unittest import mock

import requests
from django.test import SimpleTestCase

from core.harness import recorder, sheet
from core.harness.browser import first_gif_frame
from core.test_runner import MicrowebTestRunner

API = 'https://lfgss.microcosm.app/api/v1'


def live_response(request, body, status=200, headers=None):
    response = requests.Response()
    response.status_code = status
    response.reason = 'OK'
    response.headers.update(headers or {'Content-Type': 'application/json'})
    response._content = body
    response.url = request.url
    response.request = request
    return response


class RequestKeyTests(SimpleTestCase):

    def test_query_is_sorted(self):
        self.assertEqual(
            recorder.request_key('get', API + '/search?q=bike&defaults=true'),
            recorder.request_key('GET', API + '/search?defaults=true&q=bike'),
        )
        self.assertEqual(
            recorder.request_key('GET', API + '/search?q=bike&defaults=true'),
            'GET %s/search?defaults=true&q=bike anon' % API,
        )

    def test_token_presence_not_value(self):
        a = recorder.request_key('GET', API + '/whoami', {'Authorization': 'Bearer one'})
        b = recorder.request_key('GET', API + '/whoami', {'Authorization': 'Bearer two'})
        self.assertEqual(a, b)
        self.assertEqual(a, 'GET %s/whoami auth' % API)
        self.assertNotIn('one', a)
        self.assertNotEqual(a, recorder.request_key('GET', API + '/whoami', {}))

    def test_method_and_path_distinguish(self):
        self.assertNotEqual(recorder.request_key('GET', API + '/site'), recorder.request_key('POST', API + '/site'))
        self.assertNotEqual(recorder.request_key('GET', API + '/site'), recorder.request_key('GET', API + '/sites'))


class RecorderTests(SimpleTestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.network = mock.Mock(side_effect=lambda adapter, request, **kw: live_response(
            request, json.dumps({'error': None, 'data': {'id': 1, 'title': 'LFGSS'}}).encode()))
        patcher = mock.patch.object(requests.adapters.HTTPAdapter, 'send', self.network)
        patcher.start()
        self.addCleanup(patcher.stop)

    def use(self, mode, session='s1'):
        rec = recorder.Recorder(self.dir, mode, session).install()
        self.addCleanup(rec.uninstall)
        return rec

    def test_record_then_replay_round_trip(self):
        rec = self.use(recorder.RECORD)
        live = requests.get(API + '/site', params={'b': 2, 'a': 1}, headers={'Authorization': 'Bearer secret'})
        rec.uninstall()
        self.assertEqual(self.network.call_count, 1)

        files = os.listdir(os.path.join(self.dir, 'api'))
        self.assertEqual(len(files), 1)
        with open(os.path.join(self.dir, 'api', files[0])) as f:
            stored = f.read()
        self.assertNotIn('secret', stored)

        self.use(recorder.REPLAY)
        replayed = requests.get(API + '/site', params={'a': 1, 'b': 2}, headers={'Authorization': 'Bearer other'})
        self.assertEqual(self.network.call_count, 1)
        self.assertEqual(replayed.status_code, 200)
        self.assertEqual(replayed.json(), live.json())
        self.assertEqual(replayed.headers['Content-Type'], 'application/json')

    def test_replay_follows_recorded_redirect(self):
        def network(adapter, request, **kw):
            if request.url.endswith('/whoami'):
                return live_response(request, b'', 302, {'Location': API + '/profiles/54446'})
            return live_response(request, b'{"error": null, "data": {"id": 54446}}')
        self.network.side_effect = network
        rec = self.use(recorder.RECORD)
        requests.get(API + '/whoami')
        rec.uninstall()

        self.use(recorder.REPLAY)
        response = requests.get(API + '/whoami')
        self.assertEqual(response.json()['data']['id'], 54446)
        self.assertEqual(response.history[0].url, API + '/whoami')

    def test_record_reuses_answer_within_a_session(self):
        self.use(recorder.RECORD, session='s1')
        requests.get(API + '/site')
        requests.get(API + '/site')
        self.assertEqual(self.network.call_count, 1)

    def test_record_refetches_in_a_new_session(self):
        rec = self.use(recorder.RECORD, session='s1')
        requests.get(API + '/site')
        rec.uninstall()
        self.use(recorder.RECORD, session='s2')
        requests.get(API + '/site')
        self.assertEqual(self.network.call_count, 2)

    def test_missing_fixture_raises_clear_error(self):
        self.use(recorder.REPLAY)
        with self.assertRaises(recorder.FixtureMissingError) as caught:
            requests.get(API + '/conversations/1', params={'offset': 25})
        message = str(caught.exception)
        self.assertIn('GET %s/conversations/1?offset=25 anon' % API, message)
        self.assertIn('shoot --record', message)
        self.assertFalse(issubclass(recorder.FixtureMissingError, requests.RequestException))
        self.network.assert_not_called()

    def test_install_replaces_previous_recorder(self):
        first = recorder.install(self.dir, recorder.REPLAY)
        self.addCleanup(first.uninstall)
        second = recorder.install(self.dir, recorder.REPLAY)
        self.addCleanup(second.uninstall)
        self.assertIs(recorder.installed(), second)
        second.uninstall()
        self.assertIsNone(recorder.installed())


class FirstGifFrameTests(SimpleTestCase):
    # Two 1x1 frames with a global colour table of two entries.
    HEADER = b'GIF89a\x01\x00\x01\x00\x80\x00\x00' + b'\x00\x00\x00\xff\xff\xff'
    LOOP = b'!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00'
    FRAME = b'!\xf9\x04\x00\x0a\x00\x00\x00' + b',\x00\x00\x00\x00\x01\x00\x01\x00\x00' + b'\x02\x02D\x01\x00'

    def test_keeps_only_first_frame(self):
        animated = self.HEADER + self.LOOP + self.FRAME + self.FRAME + b';'
        self.assertEqual(first_gif_frame(animated), self.HEADER + self.LOOP + self.FRAME + b';')

    def test_other_data_unchanged(self):
        self.assertEqual(first_gif_frame(b'\x89PNG....'), b'\x89PNG....')
        self.assertEqual(first_gif_frame(b'GIF89a\x01'), b'GIF89a\x01')


class SummaryTests(SimpleTestCase):

    def shots(self, height_after, rows_after):
        cell = dict(label='home', width=1280, mode='light', status=200)
        return [
            dict(cell, side='before', height=1000, rows=8, identical=False),
            dict(cell, side='after', height=height_after, rows=rows_after, identical=False),
        ]

    def test_flags_taller_page_and_fewer_rows(self):
        s = sheet.page_summary({'label': 'home'}, self.shots(1101, 7), ['before', 'after'])
        self.assertTrue(s['height_flag'])
        self.assertAlmostEqual(s['height_delta'], 0.101)
        self.assertTrue(s['rows_flag'])

    def test_no_flag_within_budget(self):
        s = sheet.page_summary({'label': 'home'}, self.shots(1100, 8), ['before', 'after'])
        self.assertFalse(s['height_flag'])
        self.assertFalse(s['rows_flag'])


class TestRunnerTests(SimpleTestCase):

    def test_plain_run_excludes_browser_checks(self):
        runner = MicrowebTestRunner()
        self.assertIn('browser', runner.exclude_tags)
        self.assertIsNone(runner.pattern)  # Django's default, test*.py

    def test_browser_tag_finds_browser_modules(self):
        runner = MicrowebTestRunner(tags=['browser'])
        self.assertEqual(runner.tags, {'browser'})
        self.assertNotIn('browser', runner.exclude_tags or set())
        self.assertEqual(runner.pattern, '*test*.py')
