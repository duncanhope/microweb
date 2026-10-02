"""The moderation confirm page had an empty <title>, so the browser tab and
history showed only the address. It now names the action and the item."""
import re

from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Microcosm
from core.tests.test_bs5_base import make_site, make_user
from core.tests.test_edit_reason import load


def title(action):
    context = {'site': make_site(), 'user': make_user(), 'content': Microcosm.from_api_response(load('microcosm.json')),
               'item_type': 'microcosm', 'action': action}
    html = engines['django'].get_template('forms/moderation_item.html').render(
        context, RequestFactory().get('/moderate/'))
    return re.search(r'<title>(.*?)</title>', html, re.S).group(1)


class ModerationTitleTests(SimpleTestCase):

    def test_the_title_names_the_action_and_the_item(self):
        self.assertEqual(title('close'), 'Close Generated | LFGSS')
        self.assertEqual(title('move'), 'Move Generated | LFGSS')
