"""huddles/views.py create when an upload with the first comment fails.

The message and its first comment are already sent by then, so the view
shows the comment form's fallback page (as comments/views.py does): the
error, and the comment with the text typed, in both template trees."""
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.api.resources import Comment, Huddle
from core.tests.test_bs5_huddles import comment, huddle_data, load, request, SITE_URL, WHOAMI_URL
from huddles import views

TYPED = 'Made-up first comment with a big file'
POST = {'title': 'A made-up message', 'is_confidential': '0', 'invite': '101,102', 'firstcomment': TYPED}


def sent_comment():
    data = comment(1)
    data['markdown'], data['html'] = TYPED, '<p>%s</p>' % TYPED
    data['meta']['links'] = [{'rel': 'self', 'href': '/api/v1/comments/501'},
                             {'rel': 'up', 'href': '/api/v1/huddles/900', 'title': 'A made-up message'}]
    return Comment.from_api_response(data)


class CreateWithABadAttachmentTests(SimpleTestCase):

    def post(self, bs):
        responses = {SITE_URL: load('site.json'), WHOAMI_URL: load('whoami.json')}
        with mock.patch.object(views.fetch, 'map', return_value=[]), \
                mock.patch.object(views, 'response_list_to_dict', return_value=responses), \
                mock.patch.object(Huddle, 'create', return_value=Huddle.from_api_response(huddle_data())), \
                mock.patch.object(Huddle, 'invite') as invite, \
                mock.patch.object(Comment, 'create', return_value=sent_comment()) as create_comment, \
                mock.patch.object(views, 'process_attachments', side_effect=ValidationError('too big')):
            response = views.create(request('/huddles/create/?bs=%d' % bs, 'post', POST))
        # The message, its invites and its first comment were sent once each.
        self.assertEqual(invite.call_args.args[1:3], (900, [101, 102]))
        self.assertEqual(create_comment.call_count, 1)
        return response

    def test_the_error_is_shown_with_the_text_typed(self):
        for bs in (3, 5):
            with self.subTest(bs=bs):
                response = self.post(bs)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode('utf-8')
                self.assertIn('Sorry, one of your files was over 30 MB. Please try again.', html)
                self.assertIn('<p>%s</p>' % TYPED, html)
                self.assertIn('A made-up message', html)
                self.assertEqual('bs5.min.css' in html, bs == 5)
