"""The Bootstrap 3 membership group form wrote the group name (with |safe),
the criteria and the individuals' names into an attribute and into script
strings without escaping them, so a quote broke the page and markup in a
group name ran as script. Every group, criterion and person here is made up."""
import json
import re

from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Microcosm, Role, RoleCriteriaList, RoleProfileList
from core.tests.test_bs5_base import make_site, make_user
from core.tests.test_edit_reason import load

PAGE = {'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1, 'page': 1, 'links': []}
NASTY = 'a"b\'c</script><script>alert(1)</script>'


def render(**extra):
    context = {'site': make_site(), 'user': make_user(), 'content': Microcosm.from_api_response(load('microcosm.json'))}
    context.update(extra)
    request = RequestFactory().get('/microcosms/1/memberships/40/edit/')
    return engines['django'].get_template('forms/memberships.html').render(context, request)


def scripts(html):
    """The inline scripts, which must hold no end tag of their own."""
    return re.findall(r'<script type="text/javascript">(.*?)</script>', html, re.S)


def edit_page():
    role = Role.from_summary({'id': 40, 'microcosmId': 1, 'title': NASTY, 'moderator': False, 'banned': False,
                              'includeGuests': False, 'includeUsers': True, 'create': False, 'read': True,
                              'update': False, 'delete': False, 'closeOwn': False, 'openOwn': False,
                              'readOthers': False})
    criteria = RoleCriteriaList({'criteria': dict(PAGE, total=1, type='/api/v1/criteria', items=[
        {'id': 1, 'orGroup': 0, 'attrKey': NASTY, 'predicate': 'eq', 'value': NASTY}]), 'meta': {'links': []}})
    profiles = RoleProfileList({'profiles': dict(PAGE, total=1, type='/api/v1/profiles', items=[
        {'id': 101, 'siteId': 1, 'userId': 101, 'profileName': NASTY, 'visible': True,
         'avatar': '/api/v1/files/abc', 'meta': {'flags': {}, 'links': []}}]), 'meta': {'links': []}})
    return render(role=role, criteria=criteria, profiles=profiles, state_edit=True)


class MembershipFormEscapingTests(SimpleTestCase):

    def test_the_name_box_holds_the_name_as_text(self):
        html = edit_page()
        self.assertIn('value="a&quot;b&#x27;c&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;"', html)

    def test_no_value_ends_the_script_early(self):
        html = edit_page()
        self.assertNotIn('<script>alert(1)</script>', html)
        for script in scripts(html):
            self.assertNotIn('</script', script)

    def test_the_scripts_get_the_values_back_unchanged(self):
        html = edit_page()
        # Each value is one JavaScript string, which reads back as the original.
        page = ''.join(scripts(html))
        strings = [json.loads('"%s"' % s.replace("\\'", "'")) for s in re.findall(r'"((?:[^"\\]|\\.)*)"', page)]
        self.assertEqual(strings.count(NASTY), 5)

    def test_a_new_group_still_renders(self):
        html = render()
        self.assertIn('placeholder="Name of group" value=""', html)
        self.assertIn("value: \"\" },", html)
