"""The forum admin family on Bootstrap 5 (BS5-14): memberships.html,
forms/memberships.html (with forms/membership_toggle.html),
forms/microcosm.html and forms/moderation_item.html, with
membership_form.js and the _admin.scss partial. The family also reuses
forms/content-moderation.html, forms/metabar-moderation.html and
forms/subscribe.html, which earlier families brought over.

Every forum, group and person here is made up."""
import json
import os
import re
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Microcosm, Role, RoleCriteriaList, RoleList, RoleProfileList
from core.tests.test_bs5_base import make_site, make_user
from core.tests import test_edit_reason
from core.tests.test_edit_reason import REQUIRED, load, request
from microcosms import views

REPO = Path(settings.PROJECT_ROOT).parent
PARTIAL = REPO / 'core' / 'static' / 'themes' / '1' / 'scss' / '_admin.scss'
SCRIPTS = REPO / 'core' / 'static' / 'js' / 'bs5'

# Every template the family owns in core/templates_bs5/, and the ones it reuses.
FAMILY = ['memberships.html', 'forms/memberships.html', 'forms/membership_toggle.html', 'forms/microcosm.html',
          'forms/moderation_item.html', 'forms/content-moderation.html', 'forms/metabar-moderation.html',
          'forms/subscribe.html']
FAMILY_SCRIPTS = ['membership_form.js', 'validate.js']

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')

PAGE = {'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1, 'page': 1, 'links': []}
FORUM = {'title': 'A made-up forum', 'description': 'About made-up things', 'parentId': '0',
         'itemTypes': ['conversation', 'event'], 'visibility': 'public', 'logoUrl': ''}
TOGGLES = ['include_registered', 'include_unregistered', 'is_moderator', 'is_banned', 'can_read', 'can_create',
           'can_close_own', 'can_open_own', 'can_edit_others', 'can_delete_others']


def person(n):
    return {'id': 100 + n, 'siteId': 1, 'userId': 100 + n, 'profileName': 'rider%d' % n, 'visible': True,
            'avatar': '/api/v1/files/abc%d' % n, 'meta': {'flags': {}, 'links': []}}


def role_data(role_id=40, title='Made-up riders', microcosm_id=1, members=0, **flags):
    data = {'id': role_id, 'microcosmId': microcosm_id, 'title': title, 'moderator': False, 'banned': False,
            'includeGuests': False, 'includeUsers': False, 'create': False, 'read': False, 'update': False,
            'delete': False, 'closeOwn': False, 'openOwn': False, 'readOthers': False}
    data.update(flags)
    if members:
        data['members'] = dict(PAGE, total=members, type='/api/v1/profiles',
                               items=[person(n) for n in range(min(members, 5))])
    return data


def role_list(*roles):
    return RoleList({'roles': dict(PAGE, total=len(roles), type='/api/v1/roles', items=list(roles)),
                     'meta': {'links': [], 'permissions': {}}})


def forum(**permissions):
    data = load('microcosm.json')
    data['meta']['permissions'].update(permissions)
    return Microcosm.from_api_response(data)


def criteria(*rows):
    return RoleCriteriaList({'criteria': dict(PAGE, total=len(rows), type='/api/v1/criteria', items=list(rows)),
                             'meta': {'links': []}})


def profiles(*people):
    return RoleProfileList({'profiles': dict(PAGE, total=len(people), type='/api/v1/profiles', items=list(people)),
                            'meta': {'links': []}})


def checked(html):
    """{toggle name: the answer checked}."""
    return dict(re.findall(r'name="(\w+)" id="\w+-\d" value="(\d)" autocomplete="off" checked>', html))


class Bs5AdminTests(SimpleTestCase):
    run_view = test_edit_reason.EditReasonTests.run_view
    page = test_edit_reason.EditReasonTests.page

    def render(self, name, user=None, **extra):
        context = {'site': make_site(), 'user': user}
        context.update(extra)
        return engines['bs5'].get_template(name).render(context, RequestFactory().get('/microcosms/1/memberships/'))

    def assert_bootstrap_5_only(self, html):
        for old in ('data-toggle=', 'data-target=', 'data-dismiss=', 'sprite-', 'glyphicon', '$(', 'pull-right',
                    'js/membership_form.js', 'js/peopleWidget.js', 'formValidator.js', 'js/profilePicture.js',
                    'btn-default', 'btn-primary', 'class="green', 'class="red'):
            self.assertNotIn(old, html)

    # The family ---------------------------------------------------------------------

    def test_every_family_template_is_served_from_the_bs5_tree(self):
        for name in FAMILY:
            with self.subTest(template=name):
                origin = engines['bs5'].get_template(name).origin.name
                self.assertEqual(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR), name)

    def test_every_page_renders_without_bootstrap_3_or_jquery(self):
        user = make_user()
        pages = {
            'memberships.html': lambda: self.render('memberships.html', user, content=forum(siteOwner=True),
                                                    memberships=role_list(role_data(members=3))),
            'forms/memberships.html': lambda: self.render('forms/memberships.html', user, content=forum(),
                                                          state_edit=True, role=Role.from_summary(role_data()),
                                                          criteria=criteria(), profiles=profiles()),
            'forms/moderation_item.html': lambda: self.render('forms/moderation_item.html', user, content=forum(),
                                                              item_type='microcosm', action='delete'),
        }
        for name, render in pages.items():
            with self.subTest(template=name):
                html = render()
                self.assertIn('bs5.min.css', html)
                self.assert_bootstrap_5_only(html)
        for html in (self.forum_form(), self.forum_form(edit=True)):
            self.assertIn('bs5.min.css', html)
            self.assert_bootstrap_5_only(html)

    def test_partial_has_no_colour_literals(self):
        self.assertEqual(COLOUR_LITERAL.findall(PARTIAL.read_text()), [])
        self.assertIn('@import "admin";', (PARTIAL.parent / 'site.scss').read_text())

    def test_scripts_are_modules_without_jquery(self):
        for name in FAMILY_SCRIPTS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text()
                code = re.sub(r'(?m)^\s*//.*$', '', source)
                self.assertIsNone(re.search(r'\$\(|\$\.|jQuery', code))
                self.assertRegex(source, r'(?m)^(import|export) ')

    def test_the_member_search_is_the_people_widget(self):
        """Individuals are chosen with peopleWidget.js, which searches through
        mentions.js's ProfileSearch: no other member search."""
        source = (SCRIPTS / 'membership_form.js').read_text()
        self.assertIn("import './peopleWidget.js';", source)
        self.assertNotIn('ProfileSearch', source)
        self.assertNotIn('/api/v1/profiles', source)

    # Membership groups ------------------------------------------------------------

    def test_membership_groups(self):
        groups = role_list(
            role_data(40, 'Made-up moderators', moderator=True, members=12),
            role_data(41, 'Made-up guests', includeGuests=True, read=True),
            role_data(42, 'Made-up riders', includeUsers=True, read=True, create=True, closeOwn=True, openOwn=True),
            role_data(43, 'Made-up banned', microcosm_id=9, banned=True, members=1))
        html = self.render('memberships.html', make_user(), content=forum(owner=True), memberships=groups,
                           site_section='memberships')
        self.assertIn('<h1 class="mw-list-title">Membership Groups</h1>', html)
        self.assertIn('<a id="groupslink" href="/microcosms/1/memberships/">Membership Groups</a>', html)
        self.assertEqual(html.count('<li class="mw-row mw-membership">'), 4)
        self.assertIn('12 profiles, including:', html)
        self.assertIn('1 profile, including:', html)
        self.assertEqual(html.count('<img src="https://lfgss.microcosm.app/api/v1/files/abc'), 6)
        self.assertIn('can read, create, update and delete</strong> their own content', html)
        self.assertIn('This group includes <strong class="mw-can">people who are not signed in</strong>.', html)
        self.assertIn('This group includes <strong class="mw-can">anyone who is signed in</strong>.', html)
        self.assertIn('They <strong class="mw-can">can open and close</strong> their own', html)
        self.assertIn('<strong class="mw-cannot">cannot update</strong> items created by others.', html)
        self.assertIn('<strong class="mw-cannot">cannot read, create, update or delete</strong> any content', html)
        # The forum's own groups can be edited by its owner; a parent's are inherited.
        self.assertEqual(html.count('class="btn mw-btn btn-sm">Edit Group</a>'), 3)
        self.assertIn('href="/microcosms/1/memberships/42/edit/"', html)
        self.assertIn('<div class="mw-row-side flex-shrink-0">Inherited Group</div>', html)
        self.assertIn('id="create_membership_group" href="/microcosms/1/memberships/create/"', html)

    def test_membership_groups_as_a_guest(self):
        html = self.render('memberships.html', content=forum(), memberships=role_list(role_data(read=True)))
        self.assertNotIn('Edit Group', html)
        self.assertNotIn('create_membership_group', html)
        self.assertIn('<strong class="mw-can">can read</strong> this forum.', html)

    # The membership group form ------------------------------------------------------

    def test_create_a_membership_group(self):
        html = self.render('forms/memberships.html', make_user(), content=forum())
        self.assertIn('<title>Create membership group | LFGSS</title>', html)
        self.assertIn('Create Membership Group</h1>', html)
        self.assertIn('<form id="createForm" class="mw-item-form mw-membership-form" action="/microcosms/1/memberships/api/"'
                      ' method="POST" novalidate data-mw-membership-form data-role-id="0"'
                      ' data-done-url="/microcosms/1/memberships/">', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('id="name" name="name" placeholder="Name of group" value="" required', html)
        # A new group answers No to everything.
        self.assertEqual(checked(html), {name: '0' for name in TOGGLES})
        self.assertIn('class="btn-check" name="switch" id="criteria-and" value="and" autocomplete="off" checked>', html)
        self.assertIn('<p class="mb-0" data-mw-criteria-empty>No criteria is defined for this group.', html)
        self.assertIn('data-mw-people data-mw-invited="[]"', html)
        self.assertIn('<input type="hidden" name="invite" value="" data-mw-people-ids>', html)
        self.assertIn('id="submit">Create group</button>', html)
        self.assertNotIn('delete_membership_group', html)
        self.assertIn('<script type="module" src="/static/js/bs5/membership_form.js"></script>', html)

    def test_edit_a_membership_group(self):
        role = Role.from_summary(role_data(40, 'Made-up "riders"', includeUsers=True, read=True, create=True,
                                           closeOwn=True))
        rules = criteria({'id': 1, 'orGroup': 0, 'profileColumn': 'commentCount', 'predicate': 'gt', 'value': 1000},
                         {'id': 2, 'orGroup': 0, 'attrKey': 'is_member', 'predicate': 'eq', 'value': True},
                         {'id': 3, 'orGroup': 1, 'profileColumn': 'email', 'predicate': 'substr', 'value': '@example.com'})
        html = self.render('forms/memberships.html', make_user(), content=forum(), role=role, state_edit=True,
                           criteria=rules, profiles=profiles(person(1), dict(person(2), profileName='o\'"<b>')))
        self.assertIn('<title>Edit membership group | LFGSS</title>', html)
        self.assertIn('data-role-id="40"', html)
        self.assertIn('value="Made-up &quot;riders&quot;" required', html)
        self.assertEqual(checked(html), dict({name: '0' for name in TOGGLES}, include_registered='1', can_read='1',
                                             can_create='1', can_close_own='1'))
        self.assertIn('<li data-andor="and" data-key="commentCount" data-predicate="gt" data-value="1000"></li>', html)
        self.assertIn('<li data-andor="and" data-key="is_member" data-predicate="eq" data-value="true"></li>', html)
        self.assertIn('<li data-andor="or" data-key="email" data-predicate="substr" data-value="@example.com"></li>',
                      html)
        # The individuals reach the people widget as JSON, whatever their names hold.
        invited = re.search(r'data-mw-invited="([^"]*)"', html).group(1)
        people = json.loads(invited.replace('&quot;', '"'))
        self.assertEqual([(p['id'], p['profileName']) for p in people], [(101, 'rider1'), (102, 'o\'"<b>')])
        self.assertNotIn('<b>', invited)
        self.assertIn('id="submit">Save group</button>', html)
        self.assertIn('id="delete_membership_group" class="btn btn-danger" form="createForm" data-mw-delete-role="40"',
                      html)

    def test_what_the_script_sends_is_what_members_api_reads(self):
        """membership_form.js posts {role, profiles, criteria} as before: the view
        updates the role, then replaces its criteria and its people."""
        body = {
            'role': {'id': 40, 'title': 'Made-up riders', 'includeGuests': False, 'includeUsers': True,
                     'moderator': False, 'banned': False, 'read': True, 'create': True, 'update': False,
                     'delete': False, 'closeOwn': False, 'openOwn': False, 'readOthers': True},
            'profiles': ['101', '102'],
            'criteria': [{'orGroup': 0, 'profileColumn': 'commentCount', 'predicate': 'gt', 'value': 1000}],
        }
        req = RequestFactory().post('/microcosms/1/memberships/api/', json.dumps(body),
                                    content_type='application/json')
        req.access_token = 'token'
        ok = mock.Mock(status_code=200)
        ok.json.return_value = {'data': {'id': 7, 'orGroup': 0, 'profileColumn': 'commentCount',
                                         'predicate': 'gt', 'value': 1000}}
        with mock.patch.object(views.Role, 'update_api', return_value=mock.Mock(status_code=302)) as update, \
                mock.patch.object(views.RoleCriteria, 'delete_all_api', return_value=ok), \
                mock.patch.object(views.RoleCriteria, 'create_api', return_value=ok) as create, \
                mock.patch.object(views.RoleProfile, 'delete_all_api', return_value=ok), \
                mock.patch.object(views.RoleProfile, 'update_api', return_value=ok) as people:
            response = views.members_api(req, '1')
        self.assertEqual(response.status_code, 200)
        sent = update.call_args.args[1]
        self.assertEqual((sent.id, sent.microcosm_id, sent.title, sent.include_users), (40, 1, 'Made-up riders', True))
        self.assertEqual(create.call_args.args[3].as_dict(),
                         {'orGroup': 0, 'id': 0, 'profileColumn': 'commentCount', 'predicate': 'gt', 'value': 1000})
        self.assertEqual(people.call_args.args[3], [{'id': 101}, {'id': 102}])

    # The forum form ------------------------------------------------------------------

    def forum_form(self, edit=False, method='get', data=None, logo=''):
        if not edit:
            return self.page(views, views.create_microcosm, request('/microcosms/create/?bs=5', method, data))
        microcosm = load('microcosm.json')
        microcosm['logoUrl'] = logo
        with mock.patch.object(Microcosm, 'retrieve', return_value=Microcosm.from_api_response(microcosm)):
            return self.page(views, views.edit_microcosm, request('/microcosms/1/edit/?bs=5', method, data), '1')

    def test_the_create_form(self):
        html = self.forum_form()
        self.assertIn('<title>Create a forum | ', html)
        self.assertIn('<h1 class="mw-item-title mb-3">Create a forum</h1>', html)
        self.assertIn('<form action="" method="POST" id="microcosmForm" class="mw-item-form mw-forum-form"'
                      ' enctype="multipart/form-data" novalidate data-mw-validate>', html)
        self.assertIn('<input type="hidden" name="parentId" value="0"', html)
        self.assertIn('<input type="hidden" name="visibility" value="public"', html)
        self.assertIn('id="title" name="title" placeholder="Title of forum" maxlength="50" required value="">', html)
        self.assertIn('<div class="invalid-feedback">The name is required</div>', html)
        self.assertIn('maxlength="255" required value="">', html)
        self.assertEqual(len(re.findall(r'<input class="form-check-input" type="checkbox" name="itemTypes"', html)), 3)
        self.assertNotIn('editReason', html)
        self.assertNotIn('name="logo"', html)
        self.assertIn('>Save forum</button>', html)
        self.assertIn('<script type="module" src="/static/js/bs5/validate.js"></script>', html)
        self.assertNotIn('comments.js', html)
        self.assertNotIn('profilePicture.js', html)

    def test_the_create_form_sent_back(self):
        html = self.forum_form(method='post', data=dict(FORUM, title='', itemTypes=[]))
        self.assertIn('class="form-control is-invalid" id="title"', html)
        self.assertIn('<div class="invalid-feedback">The name is required</div>', html)
        self.assertIn('value="About made-up things"', html)
        self.assertIn('<div class="invalid-feedback d-block">%s</div>' % REQUIRED, html)

    def test_the_edit_form(self):
        html = self.forum_form(edit=True)
        self.assertIn('<title>Edit this forum | ', html)
        self.assertIn('<h1 class="mw-item-title mb-3">Edit a forum</h1>', html)
        self.assertIn('<input type="hidden" name="id" value="1"', html)
        self.assertIn('value="Generated"', html)
        self.assertNotIn(REQUIRED, html)
        self.assertIn('class="form-control" id="editReason" name="editReason" placeholder="Reason for editing"'
                      ' maxlength="150" required>', html)
        # No logo yet: the box says what to do, and there is nothing to remove.
        self.assertIn('<label class="mw-avatar-drop mw-logo-drop" data-mw-avatar-drop>', html)
        self.assertIn('<img hidden alt="The forum\'s logo">', html)
        self.assertIn('<input type="file" name="logo" id="input_logo" accept="image/*" class="visually-hidden">',
                      html)
        self.assertNotIn('remove_logo', html)
        self.assertIn('<script type="module" src="/static/js/bs5/profilePicture.js"></script>', html)
        # MicrocosmEdit has no siteId: nothing is printed for it, as on Bootstrap 3.
        self.assertNotIn('siteId', html)

    def test_the_edit_form_with_a_logo(self):
        html = self.forum_form(edit=True, logo='https://lfgss.microcosm.app/api/v1/files/abc.png')
        self.assertIn('<label class="mw-avatar-drop mw-logo-drop has-image" data-mw-avatar-drop>', html)
        self.assertIn('<img src="https://lfgss.microcosm.app/api/v1/files/abc.png" alt="The forum\'s logo">', html)
        self.assertIn('id="input_remove_logo" name="remove_logo" value="true">', html)

    def test_the_edit_form_posted_without_a_reason_says_so(self):
        html = self.forum_form(edit=True, method='post', data=dict(FORUM, id='1', editReason=''))
        self.assertIn('<h1 class="mw-item-title mb-3">Edit a forum</h1>', html)
        self.assertIn('class="form-control is-invalid" id="editReason"', html)
        self.assertIn('<div class="invalid-feedback">%s</div>' % REQUIRED, html)
        self.assertIn('value="A made-up forum"', html)
        self.assertIn('id="id_itemTypes_1" value="conversation" checked>', html)
        self.assertIn('id="id_itemTypes_0" value="microcosm">', html)

    # Moderation ----------------------------------------------------------------------

    def test_confirm_a_moderation_action(self):
        html = self.render('forms/moderation_item.html', make_user(), content=forum(), item_type='microcosm',
                           action='close')
        self.assertIn('<title>Close Generated | LFGSS</title>', html)
        self.assertIn('Do you wish to close "Generated"?', html)
        self.assertIn('<form class="d-flex flex-wrap align-items-center gap-2 mb-3 mw-moderation-confirm"'
                      ' action="do/" method="POST">', html)
        self.assertIn('<input type="hidden" name="action" value="close">', html)
        self.assertIn('<input type="hidden" name="item_type" value="microcosm">', html)
        self.assertIn('<input type="hidden" name="microcosm_id" value="1">', html)
        self.assertIn('<button type="submit" class="btn mw-btn">Close</button>', html)
        self.assertIn('<a href="/microcosms/1/">cancel and go back</a>', html)

    def test_move_picks_a_forum(self):
        content = mock.Mock(id=9, microcosm_id=1, title='A made-up conversation', breadcrumb=None,
                            meta=mock.Mock(links={}))
        microcosms = mock.Mock(microcosms=[{'id': 1, 'title': 'Generated'}, {'id': 2, 'title': 'Other &amp; more'}])
        html = self.render('forms/moderation_item.html', make_user(), content=content, item_type='conversation',
                           action='move', microcosms=microcosms)
        self.assertIn('Move A made-up conversation to:', html)
        self.assertIn('<select name="microcosm_id" class="form-select w-auto mw-min-w-0"', html)
        self.assertIn('<option value="2">Other &amp; more</option>', html)
        self.assertIn('<button type="submit" class="btn mw-btn">Go</button>', html)
        self.assertNotIn('<input type="hidden" name="microcosm_id"', html)

    def test_bootstrap_3_pages_are_unchanged(self):
        html = engines['django'].get_template('memberships.html').render(
            {'site': make_site(), 'user': make_user(), 'content': forum(siteOwner=True),
             'memberships': role_list(role_data())}, RequestFactory().get('/'))
        self.assertIn('sprite sprite-user-group', html)
        self.assertIn('class="btn btn-default pull-right"', html)
