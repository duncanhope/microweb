from unittest.mock import patch

import requests
from django.test import RequestFactory
from django.test import SimpleTestCase

from updates.views import WatcherView


class WatcherEmailToggleTests(SimpleTestCase):
    """The "Notify me by email" checkbox POSTs patch=true with emailMe to WatcherView.single."""

    def post(self, **data):
        request = RequestFactory().post('/watchers/', data)
        request.access_token = 'token'
        return request

    @patch('updates.views.Watcher.update')
    def test_patch_turns_email_on(self, mock_update):
        mock_update.return_value.status_code = requests.codes.ok
        request = self.post(updateTypeId='1', itemType='conversation', itemId='141600', emailMe='true', patch='true')

        response = WatcherView.single(request)

        self.assertEqual(response.status_code, 200)
        mock_update.assert_called_once_with(
            'testserver', {'itemType': 'conversation', 'itemId': 141600, 'sendEmail': True}, 'token')

    @patch('updates.views.Watcher.update')
    def test_patch_turns_email_off(self, mock_update):
        mock_update.return_value.status_code = requests.codes.ok
        request = self.post(updateTypeId='1', itemType='conversation', itemId='141600', emailMe='false', patch='true')

        WatcherView.single(request)

        self.assertFalse(mock_update.call_args.args[1]['sendEmail'])

    @patch('updates.views.Watcher.update')
    def test_patch_failure_is_a_bad_request(self, mock_update):
        mock_update.return_value.status_code = requests.codes.bad_request
        request = self.post(updateTypeId='1', itemType='conversation', itemId='141600', emailMe='true', patch='true')

        self.assertEqual(WatcherView.single(request).status_code, 400)
