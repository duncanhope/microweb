"""The huddles family on Bootstrap 5 (BS5-13): huddles.html, huddle.html,
modal_huddle_invite.html, modal_huddle_leave.html, forms/huddle.html and the
message row block_huddle.html (BS5-10), with peopleWidget.js and the
_huddles.scss partial.

Every huddle here is made up: the harness user's real messages never reach
a test or a fixture."""
import json
import os
import re
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase
from django.test.signals import template_rendered

from core.api.resources import Huddle, HuddleList, Profile
from core.forms.forms import CommentForm, HuddleCreate
from core.tests.test_bs5_base import make_site, make_user
from core.views import build_pagination_links
from huddles import views

REPO = Path(settings.PROJECT_ROOT).parent
DATA = Path(__file__).resolve().parent / 'data'
PARTIAL = REPO / 'core' / 'static' / 'themes' / '1' / 'scss' / '_huddles.scss'
SCRIPTS = REPO / 'core' / 'static' / 'js' / 'bs5'

# Every template the family owns in core/templates_bs5/.
FAMILY = ['huddles.html', 'huddle.html', 'modal_huddle_invite.html', 'modal_huddle_leave.html',
          'forms/huddle.html', 'block_huddle.html']
FAMILY_SCRIPTS = ['peopleWidget.js']

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')

PAGE = {'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1, 'page': 1, 'links': []}
SITE_URL, WHOAMI_URL = 'site', 'whoami'


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


def person(n, name=None):
    return {'id': 100 + n, 'siteId': 1, 'userId': 100 + n, 'profileName': name or 'rider%d' % n, 'visible': True,
            'avatar': '/api/v1/files/abc%d' % n, 'meta': {'flags': {}, 'links': []}}


def huddle_data(huddle_id=900, title='A made-up message', participants=2, confidential=False, comments=()):
    people = [person(n) for n in range(participants)]
    return {
        'id': huddle_id, 'title': title, 'isConfidential': confidential, 'participants': people,
        'totalComments': len(comments) or 3, 'lastCommentId': 77, 'lastCommentCreated': '2026-09-29T12:00:00Z',
        'lastCommentCreatedBy': people[0],
        'comments': dict(PAGE, total=len(comments), type='/api/v1/comments', items=list(comments)),
        'meta': {'created': '2026-09-28T12:00:00Z', 'createdBy': people[0], 'flags': {'watched': False},
                 'links': [{'rel': 'self', 'href': '/api/v1/huddles/%d' % huddle_id}],
                 'permissions': {'create': True, 'read': True, 'update': True, 'delete': True, 'guest': False,
                                 'moderator': False, 'owner': True, 'siteOwner': False}},
    }


def comment(n, huddle_id=900):
    return {'id': 500 + n, 'itemType': 'huddle', 'itemId': huddle_id, 'revisions': 1,
            'markdown': 'Made-up comment %d' % n, 'html': '<p>Made-up comment %d</p>' % n,
            'meta': {'created': '2026-09-29T12:00:00Z', 'createdBy': person(1), 'flags': {}, 'links': [],
                     'permissions': {}}}


def huddle_list(*huddles):
    return HuddleList({'huddles': dict(PAGE, total=len(huddles), type='/api/v1/huddles', items=list(huddles)),
                       'meta': {'links': [{'rel': 'self', 'href': '/api/v1/huddles'}]}})


def request(path, method='get', data=None):
    request = getattr(RequestFactory(), method)(path, data or {})
    request.access_token = 'token'
    request.whoami_url = WHOAMI_URL
    request.site_url = SITE_URL
    request.view_requests = []
    request.color_mode = 'auto'
    return request


class Bs5HuddlesTests(SimpleTestCase):

    def render(self, name, user=None, path='/', **extra):
        context = {'site': make_site(), 'user': user}
        context.update(extra)
        return engines['bs5'].get_template(name).render(context, RequestFactory().get(path))

    def render_huddle(self, **values):
        huddle = Huddle.from_api_response(huddle_data(**values))
        participants = json.dumps([p.as_dict for p in huddle.participants])
        return self.render('huddle.html', user=make_user(), path='/huddles/900/', content=huddle,
                           item_type='huddle', participants_json=participants,
                           comment_form=CommentForm(initial=dict(itemId=huddle.id, itemType='huddle')),
                           pagination=build_pagination_links([], huddle.comments))

    def assert_bootstrap_5_only(self, html):
        for old in ('data-toggle=', 'data-target=', 'data-dismiss=', 'sprite-', 'glyphicon', '$(',
                    'js/peopleWidget.js', 'js/comments.js', 'formValidator.js', 'textcomplete', 'js/filters.js'):
            self.assertNotIn(old, html)

    # The family ---------------------------------------------------------------------

    def test_every_family_template_is_served_from_the_bs5_tree(self):
        for name in FAMILY:
            with self.subTest(template=name):
                origin = engines['bs5'].get_template(name).origin.name
                self.assertEqual(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR), name)

    def test_every_page_renders_without_bootstrap_3_or_jquery(self):
        pages = {
            'huddles.html': lambda: self.render('huddles.html', user=make_user(),
                                                content=huddle_list(huddle_data())),
            'huddle.html': lambda: self.render_huddle(comments=[comment(1)]),
            'forms/huddle.html': lambda: self.render('forms/huddle.html', user=make_user(), form=HuddleCreate()),
        }
        for name, render in pages.items():
            with self.subTest(template=name):
                html = render()
                self.assertIn('bs5.min.css', html)
                self.assert_bootstrap_5_only(html)

    def test_partial_has_no_colour_literals(self):
        self.assertEqual(COLOUR_LITERAL.findall(PARTIAL.read_text()), [])
        self.assertIn('@import "huddles";', (PARTIAL.parent / 'site.scss').read_text())

    def test_scripts_are_modules_without_jquery(self):
        for name in FAMILY_SCRIPTS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text()
                code = re.sub(r'(?m)^\s*//.*$', '', source)
                self.assertIsNone(re.search(r'\$\(|\$\.|jQuery', code))
                self.assertRegex(source, r'(?m)^(import|export) ')

    def test_one_member_search_is_shared(self):
        """The people widget searches through mentions.js's ProfileSearch, and
        the event form's invites are the people widget: no third search."""
        self.assertRegex((SCRIPTS / 'peopleWidget.js').read_text(),
                         r"import \{[^}]*\bProfileSearch\b[^}]*\} from './mentions.js';")
        for name in ('eventForm.js', 'eventFormClasses.js'):
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text()
                self.assertNotIn('ProfileSearch', source)
                self.assertNotIn('/api/v1/profiles', source)
        self.assertIn("import './peopleWidget.js';", (SCRIPTS / 'eventForm.js').read_text())

    # Messages -------------------------------------------------------------------

    def test_messages_list(self):
        html = self.render('huddles.html', user=make_user(), path='/huddles/?unread=true', unread=True,
                           content=huddle_list(huddle_data(900, 'First made-up'), huddle_data(901, 'Second')))
        self.assertIn('<h1 class="mw-list-title"><a href="/huddles/">Messages</a></h1>', html)
        self.assertEqual(html.count('<li class="mw-row" id="huddle'), 2)
        self.assertIn('<a href="/huddles/900/newest/">First made-up</a>', html)
        self.assertIn('href="/huddles/create/" class="btn mw-btn">', html)
        self.assertIn('<form action="/huddles/" method="GET" class="mw-filters mw-options" data-mw-filters>', html)
        self.assertIn('name="unread" value="true" checked>', html)
        self.assertIn('<input type="hidden" name="type" value="huddle">', html)
        self.assertIn('<script type="module" src="/static/js/bs5/filters.js"></script>', html)

    def test_messages_list_empty_and_guest(self):
        html = self.render('huddles.html', user=make_user(), content=huddle_list())
        self.assertIn('<p class="mw-empty">You currently have no messages.</p>', html)
        self.assertNotIn('mw-rows', html)
        html = self.render('huddles.html', content=huddle_list())
        self.assertIn('<p class="mw-empty">Sign-in to read your messages.</p>', html)

    def test_rows_add_no_includes(self):
        """Each row is one {% huddle %} render, as on trunk: no include per row."""
        def templates_for(rows):
            rendered = []

            def seen(sender, template, context, **kwargs):
                rendered.append(template.name)
            template_rendered.connect(seen)
            try:
                self.render('huddles.html', user=make_user(),
                            content=huddle_list(*[huddle_data(900 + n) for n in range(rows)]))
            finally:
                template_rendered.disconnect(seen)
            return rendered
        one, five = templates_for(1), templates_for(5)
        self.assertEqual(len(five) - len(one), 4)
        self.assertEqual(five.count('block_huddle.html') - one.count('block_huddle.html'), 4)

    # A message ------------------------------------------------------------------------

    def test_message_page(self):
        html = self.render_huddle(participants=9, comments=[comment(1), comment(2)])
        self.assertIn('<div data-mw-comments>', html)
        self.assertEqual(len(re.findall(r'<li><a href="/profiles/\d+/" data-bs-toggle="tooltip"', html)), 7)
        self.assertIn('data-bs-target="#modal-huddle-invite" aria-label="Everyone who can see this message">+2</button>',
                      html)
        self.assertIn('data-bs-target="#modal-huddle-invite">Share Message</button>', html)
        self.assertIn('data-bs-target="#modal-huddle-leave">Delete Message</button>', html)
        self.assertEqual(html.count('class="mw-comment"'), 2)
        self.assertIn('Made-up comment 2', html)
        # The reply box is the conversation page's.
        self.assertIn('<section id="reply" class="mw-comment mw-reply" data-mw-reply-default', html)
        self.assertIn('<input type="hidden" name="itemType" value="huddle">', html)
        self.assertIn('<input type="hidden" name="itemId" value="900">', html)
        # Follow is a huddle's update type.
        self.assertIn('data-item-type="huddle" data-item-id="900" data-update-type="4"', html)
        self.assertIn('<input type="hidden" name="type" value="comment">', html)
        self.assertIn('<script type="module" src="/static/js/bs5/comments.js"></script>', html)
        self.assertIn('<script type="module" src="/static/js/bs5/peopleWidget.js"></script>', html)
        self.assertIn('id="formatting-help-modal"', html)

    def test_share_modal(self):
        html = self.render_huddle(participants=3)
        modal = re.search(r'<div id="modal-huddle-invite".*?</form>', html, re.S).group(0)
        self.assertIn('class="modal fade" tabindex="-1" aria-labelledby="modal-huddle-invite-title"', modal)
        self.assertIn('<form class="modal-content" action="/huddles/900/invite/" method="POST">', modal)
        self.assertIn('name="csrfmiddlewaretoken"', modal)
        self.assertEqual(modal.count('<li><a href="/profiles/'), 3)
        # Space separated, as huddles/views.py invite reads them, and the
        # people in already are left out of the search.
        self.assertIn('data-mw-people data-mw-separator=" " data-mw-members="[{&quot;id&quot;: 100,', modal)
        self.assertIn('<input type="hidden" name="invite_profile_id" value="" data-mw-people-ids>', modal)
        self.assertIn('<label class="form-label" for="mw-huddle-invite">', modal)
        self.assertIn('data-mw-people-submit disabled>Share</button>', modal)
        self.assertIn('data-bs-dismiss="modal" aria-label="Close"', modal)

    def test_leave_modal(self):
        html = self.render_huddle()
        modal = re.search(r'<div id="modal-huddle-leave".*', html, re.S).group(0)
        self.assertIn('<form action="/huddles/900/leave/" method="POST">', modal)
        self.assertIn('<button type="submit" class="btn btn-danger">Delete Message</button>', modal)
        self.assertIn('You will no longer be able to view any past or future messages', modal)

    def test_a_confidential_message_cannot_be_shared(self):
        html = self.render_huddle(participants=9, confidential=True)
        self.assertNotIn('modal-huddle-invite', html)
        self.assertNotIn('peopleWidget.js', html)
        self.assertIn('data-bs-target="#modal-huddle-leave"', html)
        self.assertIn('<li>+2</li>', html)

    # New message ------------------------------------------------------------------

    def run_view(self, view, req, *args):
        responses = {SITE_URL: load('site.json'), WHOAMI_URL: load('whoami.json')}
        with mock.patch.object(views.fetch, 'map', return_value=[]), \
                mock.patch.object(views, 'response_list_to_dict', return_value=responses):
            return view(req, *args)

    def test_new_message_form_with_a_recipient(self):
        recipient = Profile(person(7, 'made-up-friend'))
        with mock.patch.object(views.Profile, 'retrieve', return_value=recipient):
            response = self.run_view(views.create, request('/huddles/create/?to=107&bs=5'))
        html = response.content.decode('utf-8')
        self.assertIn('bs5.min.css', html)
        self.assert_bootstrap_5_only(html)
        self.assertIn('<form action="" method="POST" id="huddleForm" class="mw-item-form" '
                      'enctype="multipart/form-data" novalidate data-mw-validate>', html)
        self.assertIn('<input type="hidden" name="is_confidential" value="0">', html)
        self.assertIn('maxlength="150" required value="">', html)
        self.assertIn('<div class="invalid-feedback">Please add a subject</div>', html)
        self.assertIn('data-mw-people data-mw-invited="[{&quot;id&quot;: 107, &quot;profileName&quot;: '
                      '&quot;made-up-friend&quot;', html)
        self.assertIn('<input type="hidden" name="invite" value="" data-mw-people-ids>', html)
        self.assertIn('name="firstcomment"', html)
        self.assertIn('>Send Message</button>', html)
        self.assertIn('<script type="module" src="/static/js/bs5/peopleWidget.js"></script>', html)

    def test_a_new_message_sent_back_keeps_its_subject(self):
        data = {'title': 'x' * 151, 'is_confidential': '0', 'invite': '', 'firstcomment': ''}
        response = self.run_view(views.create, request('/huddles/create/?bs=5', 'post', data))
        html = response.content.decode('utf-8')
        self.assertIn('class="form-control is-invalid" id="title"', html)
        self.assertIn('value="%s"' % ('x' * 151), html)
        self.assertIn('The subject may not be longer than 150 characters', html)

    def test_sharing_posts_space_separated_ids(self):
        """What the Share modal posts reaches the API as the profiles chosen."""
        with mock.patch.object(views.Huddle, 'invite') as invite:
            response = views.invite(request('/huddles/900/invite/', 'post', {'invite_profile_id': '101 102'}), '900')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/huddles/900/')
        self.assertEqual(invite.call_args[0][1:3], ('900', [101, 102]))

    def test_bootstrap_3_pages_are_unchanged(self):
        response = self.run_view(views.create, request('/huddles/create/?bs=3'))
        html = response.content.decode('utf-8')
        self.assertNotIn('bs5.min.css', html)
        self.assertIn('js/peopleWidget.js', html)
        self.assertIn('sprite sprite-search-small', html)
