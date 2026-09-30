"""The reason for editing, on every edit form that asks for one: the event
and conversation forms in both template trees, and the forum form (Bootstrap
3 only). Opening the form shows no error; posting it without a reason does."""
import json
from pathlib import Path
from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from conversations import views as conversation_views
from core.api.resources import AttendeeList, Conversation, Event, Microcosm
from events import views as event_views
from microcosms import views as microcosm_views

DATA = Path(__file__).resolve().parent / 'data'
SITE_URL, WHOAMI_URL = 'site', 'whoami'
REQUIRED = 'This field is required.'
NO_ATTENDEES = {'attendees': {'total': 0, 'limit': 250, 'offset': 0, 'maxOffset': 0, 'totalPages': 1, 'page': 1,
                              'links': [], 'type': '', 'items': []},
                'meta': {'flags': {}, 'links': []}}


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


def request(path, method='get', data=None):
    request = getattr(RequestFactory(), method)(path, data or {})
    request.access_token = 'token'
    request.whoami_url = WHOAMI_URL
    request.site_url = SITE_URL
    request.view_requests = []
    request.color_mode = 'auto'
    return request


class EditReasonTests(SimpleTestCase):

    def run_view(self, views, view, req, *args, render=None):
        responses = {SITE_URL: load('site.json'), WHOAMI_URL: load('whoami.json')}
        patches = [mock.patch.object(views.fetch, 'map', return_value=[]),
                   mock.patch.object(views, 'response_list_to_dict', return_value=responses)]
        if render:
            patches.append(mock.patch.object(views, 'render', render))
        for p in patches:
            p.start()
        try:
            return view(req, *args)
        finally:
            for p in patches:
                p.stop()

    def page(self, views, view, req, *args):
        response = self.run_view(views, view, req, *args)
        self.assertEqual(response.status_code, 200)
        return response.content.decode('utf-8')

    def event_edit(self, bs, method='get', data=None):
        event = Event.from_api_response(load('event_with_comment.json'))
        with mock.patch.object(Event, 'retrieve', return_value=event), \
                mock.patch.object(Event, 'get_attendees', return_value=AttendeeList(NO_ATTENDEES)):
            return self.page(event_views, event_views.edit, request('/events/2/edit/?bs=%d' % bs, method, data), '2')

    def conversation_edit(self, bs, method='get', data=None):
        conversation = Conversation.from_api_response(load('conversation_without_comment.json'))
        with mock.patch.object(Conversation, 'retrieve', return_value=conversation):
            return self.page(conversation_views, conversation_views.edit,
                             request('/conversations/1/edit/?bs=%d' % bs, method, data), '1')

    def assert_no_error(self, html):
        self.assertIn('id="editReason"', html)
        self.assertNotIn(REQUIRED, html)
        self.assertNotIn('is-invalid" id="editReason"', html)
        self.assertNotIn('has-error', html)

    def assert_error(self, html):
        self.assertIn(REQUIRED, html)

    def test_the_event_form_opens_without_an_error(self):
        for bs in (3, 5):
            with self.subTest(bs=bs):
                html = self.event_edit(bs)
                self.assert_no_error(html)
                # And still carries the event.
                self.assertIn('Generated Event', html)

    def test_the_event_form_posted_without_a_reason_says_so(self):
        data = {'id': '2', 'microcosmId': '1', 'title': 'Generated Event', 'tz': 'Europe/London', 'editReason': ''}
        for bs in (3, 5):
            with self.subTest(bs=bs):
                self.assert_error(self.event_edit(bs, 'post', data))

    def test_the_conversation_form_opens_without_an_error(self):
        for bs in (3, 5):
            with self.subTest(bs=bs):
                html = self.conversation_edit(bs)
                self.assert_no_error(html)
                self.assertIn('value="Generated"', html)

    def test_the_conversation_form_posted_without_a_reason_says_so(self):
        data = {'id': '1', 'microcosmId': '1', 'title': 'Generated', 'editReason': ''}
        for bs in (3, 5):
            with self.subTest(bs=bs):
                self.assert_error(self.conversation_edit(bs, 'post', data))

    def test_the_forum_form_opens_without_an_error(self):
        microcosm = Microcosm.from_api_response(load('microcosm.json'))
        render = mock.Mock(return_value=HttpResponse())
        with mock.patch.object(Microcosm, 'retrieve', return_value=microcosm):
            self.run_view(microcosm_views, microcosm_views.edit_microcosm, request('/microcosms/1/edit/'), '1',
                          render=render)
        form = render.call_args.args[2]['form']
        self.assertEqual(form.errors, {})
        self.assertEqual(form['title'].value(), microcosm.title)
        self.assertEqual(form['id'].value(), microcosm.id)

    def test_the_forum_form_posted_without_a_reason_says_so(self):
        render = mock.Mock(return_value=HttpResponse())
        self.run_view(microcosm_views, microcosm_views.edit_microcosm, request('/microcosms/1/edit/', 'post', {
            'id': '1', 'title': 'Forum', 'description': 'About', 'parentId': '0', 'itemTypes': ['conversation'],
            'visibility': 'public', 'editReason': ''}), '1', render=render)
        self.assertEqual(render.call_args.args[2]['form'].errors, {'editReason': [REQUIRED]})
