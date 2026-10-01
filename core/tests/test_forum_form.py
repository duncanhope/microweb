"""Bootstrap 3 forms that told editing from creating with {% if form.id > 0 %}.
Comparing a BoundField with an int raises on Python 3, and {% if %} reads
that as false, so the forum form always said "Create a forum" and hid the
reason for editing (and with it the error when the reason was missing), and
the event form said "Post an event" when editing and never checked the
reason before posting. The views now say so with state_edit, as the
conversation and event forms already did elsewhere.

The forum form is Bootstrap 3 only for now: ?bs=5 falls back to it."""
import re
from unittest import mock

from django.test import SimpleTestCase

from core.api.resources import Microcosm
from core.tests import test_edit_reason
from core.tests.test_edit_reason import REQUIRED, load, request
from events import views as event_views
from microcosms import views

FORUM = {'title': 'A made-up forum', 'description': 'About made-up things', 'parentId': '0',
         'itemTypes': ['conversation', 'event'], 'visibility': 'public', 'logoUrl': ''}


def heading(html):
    return re.sub(r'\s+', ' ', re.search(r'<h1>(.*?)</h1>', html, re.S).group(1)).strip()


def title(html):
    return re.search(r'<title>(.*?)</title>', html, re.S).group(1).strip()


class ForumFormTests(SimpleTestCase):
    run_view = test_edit_reason.EditReasonTests.run_view
    page = test_edit_reason.EditReasonTests.page

    def edit(self, bs=3, method='get', data=None):
        microcosm = Microcosm.from_api_response(load('microcosm.json'))
        with mock.patch.object(Microcosm, 'retrieve', return_value=microcosm):
            return self.page(views, views.edit_microcosm, request('/microcosms/1/edit/?bs=%d' % bs, method, data), '1')

    def create(self, bs=3, method='get', data=None):
        return self.page(views, views.create_microcosm, request('/microcosms/create/?bs=%d' % bs, method, data))

    def assert_create(self, html):
        self.assertTrue(title(html).startswith('Create a forum |'))
        self.assertEqual(heading(html), 'Create a forum')
        self.assertNotIn('editReason', html)
        self.assertNotIn('name="logo"', html)

    def assert_edit(self, html):
        self.assertTrue(title(html).startswith('Edit this forum |'))
        self.assertEqual(heading(html), 'Edit a forum')
        self.assertIn('id="editReason"', html)
        self.assertIn('name="editReason"', html)
        # A logo can be added once the forum exists.
        self.assertIn('<input type="file" name="logo" id="input_logo"', html)

    def test_the_create_form(self):
        for bs in (3, 5):
            with self.subTest(bs=bs):
                html = self.create(bs)
                self.assert_create(html)
                self.assertIn('<input type="hidden" name="parentId" value="0"', html)

    def test_the_create_form_sent_back(self):
        html = self.create(method='post', data=dict(FORUM, title=''))
        self.assert_create(html)
        self.assertIn('The name is required', html)

    def test_a_forum_is_created(self):
        with mock.patch.object(Microcosm, 'create', autospec=True,
                               return_value=Microcosm.from_api_response({'id': 7})) as create:
            response = self.run_view(views, views.create_microcosm, request('/microcosms/create/', 'post', FORUM))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/microcosms/7/')
        sent = create.call_args.args[0].as_dict
        self.assertEqual((sent['title'], sent['parentId'], sent['itemTypes']), ('A made-up forum', 0, FORUM['itemTypes']))

    def test_the_edit_form(self):
        for bs in (3, 5):
            with self.subTest(bs=bs):
                html = self.edit(bs)
                self.assert_edit(html)
                self.assertNotIn(REQUIRED, html)
                self.assertIn('value="Generated"', html)
                self.assertIn('<input type="hidden" name="id" value="1"', html)
                # No logo yet: the upload box says what to do.
                self.assertIn('<label for="input_logo">Click here</label>', html)
                self.assertNotIn('Remove existing logo?', html)

    def test_the_edit_form_with_a_logo(self):
        data = load('microcosm.json')
        data['logoUrl'] = 'https://lfgss.microcosm.app/api/v1/files/abc.png'
        with mock.patch.object(Microcosm, 'retrieve', return_value=Microcosm.from_api_response(data)):
            html = self.page(views, views.edit_microcosm, request('/microcosms/1/edit/'), '1')
        self.assertIn('<label for="input_logo" class="active" style="background-image:url('
                      '\'https://lfgss.microcosm.app/api/v1/files/abc.png\')"></label>', html)
        self.assertIn('Remove existing logo?', html)

    def test_the_edit_form_posted_without_a_reason_says_so(self):
        html = self.edit(method='post', data=dict(FORUM, id='1', editReason=''))
        self.assert_edit(html)
        self.assertIn('<label class="control-label">* %s</label>' % REQUIRED, html)
        self.assertIn('value="A made-up forum"', html)

    def test_a_forum_is_edited(self):
        with mock.patch.object(Microcosm, 'update', autospec=True,
                               return_value=Microcosm.from_api_response({'id': 1})) as update:
            response = self.run_view(views, views.edit_microcosm, request(
                '/microcosms/1/edit/', 'post', dict(FORUM, id='1', editReason='Tidied up')), '1')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/microcosms/1/')
        sent = update.call_args.args[0].as_dict
        self.assertEqual((sent['id'], sent['title'], sent['meta']), (1, 'A made-up forum', {'editReason': 'Tidied up'}))


class EventFormEditModeTests(SimpleTestCase):
    """The Bootstrap 3 event form's heading and reason check."""
    run_view = test_edit_reason.EditReasonTests.run_view
    page = test_edit_reason.EditReasonTests.page
    event_edit = test_edit_reason.EditReasonTests.event_edit

    def test_editing_an_event(self):
        html = self.event_edit(3)
        self.assertTrue(title(html).startswith('Edit event |'))
        self.assertEqual(heading(html), 'Edit event')
        self.assertIn(",'editReason':['not_empty']", html)
        self.assertIn(",'editReason:not_empty' : \"* This is a required field\"", html)

    def test_editing_an_event_sent_back(self):
        data = {'id': '2', 'microcosmId': '1', 'title': 'Generated Event', 'tz': 'Europe/London', 'editReason': ''}
        html = self.event_edit(3, 'post', data)
        self.assertEqual(heading(html), 'Edit event')
        self.assertIn(",'editReason':['not_empty']", html)

    def test_posting_an_event(self):
        html = self.page(event_views, event_views.create, request('/microcosms/1/create/event/?bs=3'), '1')
        self.assertTrue(title(html).startswith('Post an event |'))
        self.assertEqual(heading(html), 'Post an event')
        self.assertNotIn("'editReason'", html)
