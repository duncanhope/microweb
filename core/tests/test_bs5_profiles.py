"""The profiles family on Bootstrap 5 (BS5-09): profile.html, profiles.html,
block_profile.html, block_list_comments.html, ignored.html, the profile and
notification settings forms, their scripts and Sass partial, and the member
preview links in both footers."""
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Ignored, Profile, ProfileList, Search, UpdatePreference
from core.forms.forms import ProfileEdit
from core.tests.test_bs5_base import make_site, make_user

REPO = Path(settings.PROJECT_ROOT).parent
DATA = Path(__file__).resolve().parent / 'data'
PARTIAL = REPO / 'core' / 'static' / 'themes' / '1' / 'scss' / '_profiles.scss'
SCRIPTS = REPO / 'core' / 'static' / 'js' / 'bs5'

# Every template the family owns in core/templates_bs5/.
FAMILY = [
    'profile.html', 'profiles.html', 'block_profile.html', 'block_list_comments.html', 'ignored.html',
    'forms/profile.html', 'forms/update_settings.html',
]
FAMILY_SCRIPTS = ['filters.js', 'profilePicture.js', 'updateSettings.js']

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')

PAGE = {'total': 2, 'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1, 'page': 1, 'links': [], 'type': ''}


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


def profile_data(**overrides):
    data = load('profile.json')
    data.update(itemCount=560, commentCount=155850, **overrides)
    return data


def conversation_summary():
    return load('microcosm_with_items.json')['items']['items'][1]['item']


def search():
    """A member's recent activity: a comment on a conversation, and a conversation."""
    comment = load('conversation_with_paginated_comments.json')['comments']['items'][0]
    result = {'rank': 1, 'lastModified': '2026-09-29T12:00:00Z', 'highlight': '', 'unread': False}
    return Search.from_api_response({'query': {}, 'results': dict(PAGE, items=[
        dict(result, itemType='comment', item=comment, parentItemType='conversation',
             parentItem=conversation_summary()),
        dict(result, itemType='conversation', item=conversation_summary()),
    ])})


def people():
    frodo, sam = profile_data(), profile_data(id=6, profileName='Sam', avatar='https://www.gravatar.com/avatar/s')
    return ProfileList({'profiles': dict(PAGE, items=[frodo, sam]), 'meta': {'flags': {}, 'links': []}})


class Bs5ProfilesTests(SimpleTestCase):

    def render(self, name, user=None, path='/profiles/5/', **extra):
        request = RequestFactory().get(path)
        context = {'site': make_site(), 'user': user, 'content': Profile(profile_data(), summary=False),
                   'item_type': 'profile', 'search': search()}
        context.update(extra)
        return engines['bs5'].get_template(name).render(context, request)

    def render_people(self, user=None, **extra):
        context = dict(content=people(), q='', top=True, online=False, following=False,
                       alphabet='abc', filter_name='most comments', item_type=None)
        context.update(extra)
        return self.render('profiles.html', user=user, path='/profiles/?top=true', **context)

    def render_settings(self, **extra):
        preferences = UpdatePreference.from_list([
            {'profileId': 5, 'id': 2, 'description': 'When a comment of yours is replied to', 'sendEmail': True,
             'sendSMS': False},
            {'profileId': 5, 'id': 1, 'description': 'When a comment has been posted in an item you are watching',
             'sendEmail': False, 'sendSMS': False},
        ])
        context = dict(content=preferences, globaloptions=SimpleNamespace(emailNotifications=True))
        context.update(extra)
        return self.render('forms/update_settings.html', user=make_user(), path='/updates/settings/', **context)

    def assert_bootstrap_5_only(self, html):
        self.assertNotIn('data-toggle=', html)
        self.assertNotIn('data-target=', html)
        self.assertNotIn('data-dismiss=', html)
        self.assertNotIn('sprite-', html)
        self.assertNotIn('$(', html)

    def test_every_family_template_is_served_from_the_bs5_tree(self):
        for name in FAMILY:
            with self.subTest(template=name):
                origin = engines['bs5'].get_template(name).origin.name
                self.assertEqual(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR), name)

    def test_every_family_template_renders_without_bootstrap_3_or_jquery(self):
        member = make_user()
        result = search().results.items[0]
        extra = {
            'profiles.html': dict(content=people(), alphabet='abc'),
            'block_profile.html': dict(profile={'item': people().profiles.items[0]}),
            'block_list_comments.html': dict(result=result),
            'ignored.html': dict(content=Ignored.from_api_response({'ignored': dict(PAGE, items=[])})),
            'forms/profile.html': dict(form=ProfileEdit({'id': 5, 'profileName': 'Frodo'})),
            'forms/update_settings.html': dict(content=[], globaloptions=SimpleNamespace(emailNotifications=True)),
        }
        for name in FAMILY:
            for user in (None, member):
                if name.startswith('forms/') and not user:
                    continue  # members only: the views require a signed-in member
                with self.subTest(template=name, member=bool(user)):
                    self.assert_bootstrap_5_only(self.render(name, user=user, **extra.get(name, {})))

    def test_partial_has_no_colour_literals(self):
        self.assertEqual(COLOUR_LITERAL.findall(PARTIAL.read_text()), [])
        self.assertIn('@import "profiles";', (PARTIAL.parent / 'site.scss').read_text())

    def test_scripts_are_modules_without_jquery(self):
        for name in FAMILY_SCRIPTS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text()
                code = re.sub(r'(?m)^\s*//.*$', '', source)
                self.assertIsNone(re.search(r'\$\(|\$\.|jQuery', code))
                self.assertRegex(source, r'(?m)^(import|export) ')

    # profile.html --------------------------------------------------------------

    def test_guest_profile(self):
        html = self.render('profile.html')
        self.assertIn('<h1 class="mw-profile-name"><a href="/profiles/5/">Frodo</a></h1>', html)
        self.assertIn('<img class="mw-profile-avatar" src="https://lfgss.microcosm.app/api/v1/files/', html)
        self.assertIn('<span stat="155850"><a href="/search?type=comment&amp;authorId=5">155,850</a></span> comments', html)
        self.assertIn('<a href="/profiles/">People</a>', html, 'the breadcrumb to People')
        # Most recent activity: a comment row and a conversation row.
        self.assertIn('>Most recent activity</h2>', html)
        self.assertIn('class="mw-prose mw-excerpt-text"', html)
        self.assertIn('<a href="/comments/1/incontext/">Pinned and closed</a>', html)
        self.assertEqual(html.count('<li class="mw-row'), 2)
        # Send Message opens the sign-in modal; no member actions.
        self.assertIn('data-bs-toggle="modal" data-bs-target="#modal-signin">', html)
        self.assertNotIn('data-mw-subscribe', html)
        self.assertNotIn('ignore_form', html)
        self.assertNotIn('microweb_templates', html)

    def test_someone_elses_profile(self):
        content = Profile(profile_data(), summary=False)
        content.meta.permissions.admin = False
        html = self.render('profile.html', user=make_user(), content=content)
        self.assertIn('<a href="/huddles/create/?to=5" class="btn mw-btn">', html)
        self.assertIn('data-mw-subscribe data-url="/watchers/" data-item-type="profile" data-item-id="5" '
                      'data-update-type="1"', html)
        self.assertIn('>Follow @Frodo</button>', html)
        self.assertIn('<form action="/ignore/" method="POST" id="ignore_form"', html)
        self.assertIn('<input type="hidden" name="item_type" value="profile">', html)
        self.assertIn('>Ignore</button>', html)
        self.assertNotIn('patch_form', html)

    def test_admin_grants_membership(self):
        content = Profile(profile_data(), summary=False)
        content.meta.permissions.admin = True
        html = self.render('profile.html', user=make_user(), content=content)
        self.assertIn('<form action="/profiles/5/patch/" method="POST" id="patch_form"', html)
        self.assertIn('<button type="submit" name="member" value="true" class="btn mw-btn btn-sm">Grant membership', html)

    def test_own_profile(self):
        user = make_user()
        user.id = 5
        html = self.render('profile.html', user=user)
        self.assertIn('<a href="/profiles/5/edit/" class="btn mw-btn">', html)
        self.assertIn('<a href="/ignored/" class="btn mw-btn">', html)
        self.assertNotIn('Send Message', html)
        self.assertNotIn('>Actions</h2>', html)

    def test_profile_with_no_activity(self):
        html = self.render('profile.html', search=Search.from_api_response({'query': {}}))
        self.assertIn('This person has not yet posted anything.', html)
        self.assertNotIn('mw-rows', html)

    # profiles.html and block_profile.html -----------------------------------------

    def test_people_list(self):
        html = self.render_people()
        self.assertEqual(html.count('<li class="mw-row mw-person" id="'), 2)
        self.assertIn('<strong>@Sam</strong>', html)
        self.assertNotIn('send message', html, 'guests get no send message')
        self.assertNotIn('bi-person', html, 'no type icon in the people list')
        self.assertIn('most comments</span>', html)
        self.assertIn('<script type="module" src="/static/js/bs5/filters.js">', html)
        self.assertNotIn('data-mw-subscribe', html)

    def test_people_filters(self):
        html = self.render_people(q='b', online=True)
        self.assertIn('<form action="/profiles/" method="GET" class="mw-filters" data-mw-filters>', html)
        self.assertIn('<option value="b" selected>b</option>', html)
        self.assertIn('name="online" value="true" checked>', html)
        self.assertIn('name="top" value="true" checked>', html)
        self.assertNotIn('name="following" value="true" checked', html)
        # A longer name search stays selectable, so other filters keep it.
        html = self.render_people(q='fro')
        self.assertIn('<option value="fro" selected>fro</option>', html)

    def test_member_people_list(self):
        html = self.render_people(user=make_user())
        self.assertIn('<a class="mw-person-message" href="/huddles/create/?to=6">send message</a>', html)
        # Follow the People page: new member notifications.
        self.assertIn('data-item-type="profile" data-item-id="0" data-update-type="9"', html)
        self.assertIn('>Follow</button>', html)

    def test_ignored_person_has_its_icon(self):
        item = Ignored.from_api_response({'ignored': dict(PAGE, items=[{'itemType': 'profile', 'item': profile_data()}])})
        html = self.render('block_profile.html', profile=item.items[0])
        self.assertIn('id="profile5"', html)
        self.assertIn('role="img" aria-label="Profile"', html)

    # ignored.html ----------------------------------------------------------------

    def test_ignored_items(self):
        content = Ignored.from_api_response({'ignored': dict(PAGE, items=[
            {'itemType': 'profile', 'item': profile_data()},
            {'itemType': 'conversation', 'item': conversation_summary()},
        ])})
        html = self.render('ignored.html', user=make_user(), content=content)
        self.assertIn('<h1 class="mw-list-title">Ignored Items</h1>', html)
        self.assertEqual(html.count('<li class="mw-row'), 2)
        html = self.render('ignored.html', user=make_user(), content=Ignored.from_api_response({}))
        self.assertIn('You are not ignoring anything.', html)

    # forms/profile.html -------------------------------------------------------------

    def test_profile_form(self):
        user = make_user()
        user.avatar = '/api/v1/files/abc'
        html = self.render('forms/profile.html', user=user,
                           form=ProfileEdit({'id': 54446, 'profileName': 'duncs', 'markdown': 'Hello'}))
        self.assertIn('<form id="profileform" class="mw-item-form" action="/profiles/54446/edit/" method="POST" '
                      'enctype="multipart/form-data" novalidate data-mw-validate>', html)
        self.assertIn('value="duncs" placeholder="Enter username..." maxlength="25" minlength="2" '
                      'pattern="[^@+\\s]+" required>', html)
        # The avatar box shows the uploaded avatar; profilePicture.js previews a new one.
        self.assertIn('<label class="mw-avatar-drop has-image" data-mw-avatar-drop>', html)
        self.assertIn('<img src="https://lfgss.microcosm.app/api/v1/files/abc" alt="Your avatar">', html)
        self.assertIn('<input id="avatar" name="avatar" type="file" accept="image/*" class="visually-hidden">', html)
        self.assertIn('<script type="module" src="/static/js/bs5/profilePicture.js">', html)
        # The bio is the comment box without its own form.
        self.assertIn('id="mw-editor-markdown" name="markdown" maxlength="5000">Hello</textarea>', html)
        self.assertEqual(html.count('<form'), 3, 'the navbar search, the profile form and the sign-out form')
        self.assertIn('/static/js/bs5/comments.js', html)

    def test_profile_form_errors_and_gravatar(self):
        form = ProfileEdit({'id': 54446, 'profileName': 'a b'})
        form.is_valid()
        html = self.render('forms/profile.html', user=make_user(), form=form)
        self.assertIn('class="form-control is-invalid" id="edit_profile_name"', html)
        self.assertIn('Profile name cannot contain spaces ( )', html)
        self.assertIn('<label class="mw-avatar-drop" data-mw-avatar-drop>', html)
        self.assertIn('<img hidden alt="Your avatar">', html)

    # forms/update_settings.html ----------------------------------------------------------

    def test_notification_settings(self):
        html = self.render_settings()
        self.assertIn('<form action="" method="POST" class="mw-item-form" data-mw-settings>', html)
        self.assertIn('id="profile_receive_email" name="profile_receive_email" type="checkbox" checked '
                      'data-mw-group="email" data-mw-master>', html)
        # One row per preference, in id order, each with its hidden id.
        self.assertLess(html.index('send_email_1'), html.index('send_email_2'))
        self.assertIn('<input type="hidden" name="id_1" value="1">', html)
        self.assertIn('name="send_email_1" type="checkbox" data-mw-group="email">', html)
        self.assertIn('name="send_email_2" type="checkbox" checked data-mw-group="email">', html)
        self.assertIn('<label for="send_email_2">When a comment of yours is replied to</label>', html)
        self.assertIn('<script type="module" src="/static/js/bs5/updateSettings.js">', html)

    # The member preview links (ticket 12) ---------------------------------------------------

    def test_bootstrap_5_footer_goes_back_to_the_classic_design(self):
        html = self.render('profiles.html', path='/profiles/?top=true&offset=25&bs=5',
                           content=people(), alphabet='abc')
        self.assertIn('<a href="?top=true&amp;offset=25&amp;bs=3" rel="nofollow">Back to the classic design</a>', html)

    def test_bootstrap_3_footer_offers_members_the_new_design(self):
        template = engines['django'].get_template('base.html')
        request = RequestFactory().get('/profiles/?top=true')
        context = {'site': make_site(), 'user': None}
        self.assertNotIn('Try the new design', template.render(context, request))
        user = make_user()
        user.meta = SimpleNamespace(stats={'unreadHuddles': 0}, links={})
        html = template.render(dict(context, user=user), request)
        self.assertIn('<a href="?top=true&amp;bs=5" rel="nofollow">Try the new design (beta)</a>', html)
