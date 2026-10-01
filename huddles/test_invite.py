"""huddles/views.py invite with no one to invite: nothing is sent to the
API, and the member goes back to the message, as after any invite."""
from unittest import mock

from django.test import SimpleTestCase

from core.tests.test_bs5_huddles import request
from huddles import views


class EmptyInviteTests(SimpleTestCase):

    def test_an_empty_invite_goes_back_to_the_message(self):
        for data in ({}, {'invite_profile_id': ''}, {'invite_profile_id': '  '}):
            with self.subTest(data=data), mock.patch.object(views.Huddle, 'invite') as invite:
                response = views.invite(request('/huddles/900/invite/', 'post', data), '900')
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response['Location'], '/huddles/900/')
                invite.assert_not_called()

    def test_the_bootstrap_3_page_invites_one_id(self):
        """huddle.html on Bootstrap 3 posts each person chosen on their own."""
        with mock.patch.object(views.Huddle, 'invite') as invite:
            response = views.invite(request('/huddles/900/invite/', 'post', {'invite_profile_id': '101'}), '900')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(invite.call_args.args[1:3], ('900', [101]))
