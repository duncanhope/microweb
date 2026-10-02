"""members_api reported a failed API call with print(), which gunicorn
sends nowhere useful. It now logs an error through the module logger."""
import io
import json
from contextlib import redirect_stdout
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Role, RoleCriteria
from microcosms import views

ROLE = {'id': 40, 'microcosmId': 1, 'title': 'Made-up riders', 'moderator': False, 'banned': False,
        'includeGuests': False, 'includeUsers': False, 'create': False, 'read': True, 'update': False,
        'delete': False, 'closeOwn': False, 'openOwn': False, 'readOthers': False}


def post(data):
    request = RequestFactory().post('/microcosms/1/memberships/api/', json.dumps(data),
                                    content_type='application/json')
    request.access_token = 'token'
    return request


def failed(text):
    return mock.Mock(status_code=500, text=text)


class MembersApiLoggingTests(SimpleTestCase):

    def call(self, data):
        out = io.StringIO()
        with redirect_stdout(out), self.assertLogs('microcosm.views', 'ERROR') as logs:
            response = views.members_api(post(data), '1')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(out.getvalue(), '')
        return logs.output

    def test_a_failed_delete_is_logged(self):
        with mock.patch.object(Role, 'delete_api', return_value=failed('made-up failure')):
            output = self.call({'deleteRole': 40})
        self.assertEqual(output, ['ERROR:microcosm.views:role delete: made-up failure'])

    def test_a_failed_update_is_logged_with_the_role(self):
        with mock.patch.object(Role, 'update_api', return_value=failed('made-up failure')):
            output = self.call({'role': ROLE})
        self.assertEqual(len(output), 1)
        self.assertIn('role: made-up failure', output[0])
        self.assertIn('"title": "Made-up riders"', output[0])

    def test_a_failed_criteria_reset_is_logged(self):
        with mock.patch.object(Role, 'update_api', return_value=mock.Mock(status_code=302)), \
                mock.patch.object(RoleCriteria, 'delete_all_api', return_value=failed('made-up failure')):
            output = self.call({'role': ROLE})
        self.assertEqual(output, ['ERROR:microcosm.views:role criteria delete all: made-up failure'])
