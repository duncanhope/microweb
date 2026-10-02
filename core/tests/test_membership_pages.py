"""The create and edit membership group pages only show the form; the form
saves through members_api. A POST to either page returned nothing, which
Django turned into a 500. It is now refused as a method the page lacks."""
from django.test import SimpleTestCase

from core.tests.test_edit_reason import request
from microcosms import views


class MembershipPagePostTests(SimpleTestCase):

    def test_posting_to_the_create_page_is_refused(self):
        response = views.create_members(request('/microcosms/1/memberships/create/', 'post'), '1')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response['Allow'], 'GET, HEAD')

    def test_posting_to_the_edit_page_is_refused(self):
        response = views.edit_members(request('/microcosms/1/memberships/40/edit/', 'post'), '1', '40')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response['Allow'], 'GET, HEAD')
