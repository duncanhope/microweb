"""The event maps: the event page in both template trees and the event form
(Bootstrap 3 only). Google's layer comes from the Maps JavaScript API's
current loader; the Thunderforest layers need THUNDERFOREST_API_KEY, and
without one the maps offer OpenStreetMap's standard tiles instead."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, override_settings

from events import views

REPO = Path(settings.PROJECT_ROOT).parent
DATA = Path(__file__).resolve().parent / 'data'
JS = REPO / 'core' / 'static' / 'js'
TEMPLATES = [REPO / 'core' / 'templates' / 'event.html', REPO / 'core' / 'templates' / 'forms' / 'event.html',
             REPO / 'core' / 'templates_bs5' / 'event.html']
# The scripts that choose the map's layers.
LAYER_SCRIPTS = [JS / 'leaflet.js', JS / 'bs5' / 'eventMap.js']
MAP_SCRIPTS = [JS / 'eventMap.js', JS / 'eventFormClasses.js'] + LAYER_SCRIPTS
EVENT_URL, ATTENDEES_URL, SITE_URL, WHOAMI_URL = 'event', 'attendees', 'site', 'whoami'
KEY = 'notarealkey0123'


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


def responses(event=None):
    return {
        EVENT_URL: event,
        ATTENDEES_URL: {'attendees': {'total': 0, 'limit': 250, 'offset': 0, 'maxOffset': 0, 'totalPages': 1,
                                      'page': 1, 'links': [], 'type': '', 'items': []},
                        'meta': {'flags': {}, 'links': []}},
        SITE_URL: load('site.json'),
        WHOAMI_URL: load('whoami.json'),
    }


def request(path):
    request = RequestFactory().get(path)
    request.access_token = 'token'
    request.whoami_url = WHOAMI_URL
    request.site_url = SITE_URL
    request.view_requests = []
    request.color_mode = 'auto'
    return request


class EventMapPagesTests(SimpleTestCase):

    def event_page(self, bs):
        event = load('event_with_comment.json')
        start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=10)
        event.update(when=start.strftime('%Y-%m-%dT%H:%M:%SZ'), duration=120, where='IKEA Croydon', lat=51.38,
                     lon=-0.12, north=51.39, west=-0.13, south=51.37, east=-0.11, rsvpLimit=0)
        with mock.patch.object(views.Event, 'build_request', return_value=(EVENT_URL, {}, {})), \
                mock.patch.object(views.Event, 'build_attendees_request', return_value=(ATTENDEES_URL, {}, {})), \
                mock.patch.object(views.fetch, 'map', return_value=[]), \
                mock.patch.object(views, 'response_list_to_dict', return_value=responses(event)):
            response = views.single(request('/events/2/?bs=%d' % bs), '2')
        self.assertEqual(response.status_code, 200)
        return response.content.decode('utf-8')

    def form_page(self):
        with mock.patch.object(views.fetch, 'map', return_value=[]), \
                mock.patch.object(views, 'response_list_to_dict', return_value=responses()):
            response = views.create(request('/microcosms/1/create/event/'), '1')
        self.assertEqual(response.status_code, 200)
        return response.content.decode('utf-8')

    def pages(self):
        return {'bs3 event': self.event_page(3), 'bs5 event': self.event_page(5), 'event form': self.form_page()}

    def test_every_map_loads_google_with_the_current_loader(self):
        for name, html in self.pages().items():
            with self.subTest(page=name):
                self.assertNotIn('maps.google.com/maps/api/js', html)
                self.assertIn('importLibrary', html)
                self.assertIn('v: "weekly"', html)
                self.assertEqual(html.count('maps.${c}apis.com/maps/api/js'), 1)

    def test_every_map_gets_the_thunderforest_key(self):
        with override_settings(THUNDERFOREST_API_KEY=KEY):
            for name, html in self.pages().items():
                with self.subTest(page=name):
                    self.assertIn(KEY, html)

    def test_no_key_is_an_empty_key(self):
        with override_settings(THUNDERFOREST_API_KEY=''):
            pages = self.pages()
        self.assertIn('data-thunderforest-key=""', pages['bs5 event'])
        self.assertIn("thunderforestKey : ''", pages['bs3 event'])
        self.assertIn("thunderforestKey : ''", pages['event form'])


class EventMapSourcesTests(SimpleTestCase):

    def test_no_template_asks_for_a_retired_google_version(self):
        for path in TEMPLATES:
            with self.subTest(template=path.name):
                source = path.read_text()
                self.assertIsNone(re.search(r'maps/api/js\?v=3\.\d', source))
                self.assertNotIn('sensor=false', source)

    def test_thunderforest_tiles_always_carry_the_key(self):
        for path in MAP_SCRIPTS:
            with self.subTest(script=path.name):
                for url in re.findall(r'''['"](https://[^'"]*thunderforest\.com/[^'"]*)['"]''', path.read_text()):
                    self.assertIn('?apikey=', url)

    def test_without_a_key_the_maps_offer_openstreetmap(self):
        for path in LAYER_SCRIPTS:
            with self.subTest(script=path.name):
                source = path.read_text()
                self.assertIn("'https://tile.openstreetmap.org/{z}/{x}/{y}.png'", source)
                self.assertIn('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
                              'contributors', source)

    def test_the_other_map_scripts_use_the_shared_layers(self):
        for path in (JS / 'eventMap.js', JS / 'eventFormClasses.js'):
            with self.subTest(script=path.name):
                source = path.read_text()
                self.assertNotIn('thunderforest.com', source)
                self.assertIn('L.Google.addBaseLayers(', source)


class ThunderforestSettingTests(SimpleTestCase):

    def test_the_key_is_optional_and_empty_by_default(self):
        self.assertIsInstance(settings.THUNDERFOREST_API_KEY, str)
        for name in ('local_settings.py.sample', 'travis_settings.py'):
            with self.subTest(settings=name):
                self.assertRegex((REPO / 'microweb' / name).read_text(),
                                 r"(?m)^THUNDERFOREST_API_KEY = (''|os\.getenv\('THUNDERFOREST_API_KEY', ''\))$")

    def test_production_reads_the_key_from_the_environment(self):
        source = (REPO / 'microweb' / 'local_settings.py.production').read_text()
        self.assertIn("THUNDERFOREST_API_KEY = os.getenv('THUNDERFOREST_API_KEY', '')", source)
