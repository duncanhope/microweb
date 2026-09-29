"""The forum lists family on Bootstrap 5 (BS5-07): microcosms.html, microcosm.html,
their row includes, pagination, breadcrumbs and the metabar forms."""
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Microcosm
from core.tests.test_bs5_base import make_site, make_user
from core.views import build_pagination_links

DATA = Path(__file__).resolve().parent / 'data'
PARTIAL = Path(settings.PROJECT_ROOT).parent / 'core' / 'static' / 'themes' / '1' / 'scss' / '_lists.scss'

# Every template the family owns in core/templates_bs5/.
FAMILY = [
    'microcosms.html', 'microcosm.html',
    'block_microcosm.html', 'block_conversation.html', 'block_event.html',
    'block_row_stats.html', 'block_row_forum.html', 'block_post_buttons.html',
    'pagination.html', 'breadcrumbs.html',
    'forms/mark-read.html', 'forms/subscribe.html', 'forms/metabar-moderation.html',
]

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')


def site():
    return make_site(site_id=5, meta=SimpleNamespace(stats={
        'totalProfiles': 71254, 'onlineProfiles': 328, 'totalConversations': 245478,
        'totalEvents': 1000, 'totalComments': 8049899}))


class Bs5ListsTests(SimpleTestCase):

    def setUp(self):
        with open(DATA / 'microcosm_with_items.json') as f:
            data = json.load(f)['data']
        self.content = Microcosm.from_api_response(data)
        self.pagination = build_pagination_links(data['items']['links'], self.content.items)

    def render(self, name, user=None, permissions=None, **extra):
        if permissions:
            for key, value in permissions.items():
                setattr(self.content.meta.permissions, key, value)
        request = RequestFactory().get('/microcosms/7/')
        context = {'site': site(), 'user': user, 'content': self.content, 'item_type': 'microcosm',
                   'pagination': self.pagination}
        context.update(extra)
        return engines['bs5'].get_template(name).render(context, request)

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
                self.assertEqual(os.path.dirname(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR)),
                                 os.path.dirname(name))

    def test_every_family_template_renders_without_bootstrap_3_or_jquery(self):
        item = self.content.items.items[1]
        for name in FAMILY:
            for user in (None, make_user()):
                with self.subTest(template=name, member=bool(user)):
                    html = self.render(name, user=user, item=item.item, microcosm=self.content.items.items[0],
                                       showForum=True)
                    self.assert_bootstrap_5_only(html)
                    if not name.startswith('microcosm'):
                        self.assertNotIn('onclick', html, 'family partials carry no inline script')

    def test_partial_has_no_colour_literals(self):
        source = PARTIAL.read_text()
        self.assertEqual(COLOUR_LITERAL.findall(source), [])
        self.assertIn('@import "lists";', (PARTIAL.parent / 'site.scss').read_text())

    # microcosm.html -------------------------------------------------------------

    def test_listing_rows(self):
        html = self.render('microcosm.html')
        rows = html.split('<ul class="list-unstyled mw-rows">')[1].split('<div class="mw-list-footer">')[0]
        self.assertEqual(rows.count('<li class="mw-row'), 4)
        # Pinned, closed and unread.
        self.assertIn('<li class="mw-row mw-row-pinned" id="microcosm100"', rows)
        self.assertIn('aria-label="Closed conversation"', rows)
        self.assertEqual(rows.count('<span class="badge text-bg-warning">NEW</span>'), 2)
        # A subforum with its children, stats and the latest update.
        self.assertIn('class="mw-subforum-logo"> Tuesday Club</a>', rows)
        self.assertIn('>Wednesday Club</a>', rows)
        self.assertIn('class="mw-subforum-logo"', rows)
        self.assertIn('<span stat="1234">1,234</span> conversations', rows)
        self.assertIn('<a href="/conversations/300/" title="A very long conversation title that the row truncates">'
                      'A very long conversation titl…</a>', rows)
        # An event with its date and place.
        self.assertIn('<time class="plain" datetime="2026-09-20T09:00:00" itemprop="startDate">Sep 20th</time>', rows)
        self.assertIn('>Regent\'s Park, London</span>', rows)
        self.assertIn('aria-label="Event"', rows)
        # The latest reply.
        self.assertIn('<a href="/comments/9002/incontext/">replied</a>', rows)

    def test_pagination_jump_form(self):
        html = self.render('pagination.html')
        self.assertIn('<form name="paginationByOffset" method="GET" class="mw-page-jump" data-initial="1" '
                      'data-limit="25" data-max="3">', html)
        self.assertIn('inputmode="numeric"', html)
        self.assertIn('of 3', html)
        self.assertIn('<li class="page-item active" aria-current="page"><a class="page-link" href="/microcosms/7/">1</a>',
                      html)
        self.assertIn('href="/microcosms/7/?offset=25" rel="next">2</a>', html)
        self.assertIn('>Last</a>', html)

    def test_pagination_hidden_for_one_page(self):
        self.assertEqual(self.render('pagination.html', pagination={'total_pages': 1}).strip(), '')

    def test_guest_sidebar_opens_the_signin_modal(self):
        html = self.render('microcosm.html')
        self.assertEqual(html.count('data-bs-toggle="modal" data-bs-target="#modal-signin"'), 2)
        self.assertNotIn('data-mw-subscribe', html)
        self.assertNotIn('mark-read-module', html)
        self.assertIn('Who has access to this forum?', html)

    def test_member_controls(self):
        html = self.render('microcosm.html', user=make_user())
        self.assertIn('id="create_conversation" href="/microcosms/7/create/conversation/"', html)
        self.assertIn('id="create_event"', html)
        self.assertNotIn('create_microcosm', html)
        # The Follow control, for metabar.js.
        self.assertIn('data-mw-subscribe data-url="/watchers/" data-item-type="microcosm" data-item-id="7" '
                      'data-update-type="8" data-subscribed="false" data-state="off"', html)
        # Mark everything read: a plain form posting this forum.
        form = html.split('id="mark-read-module">')[1].split('</form>')[0]
        self.assertIn('name="item_id" value="7"', form)
        self.assertIn('name="return_path" value="/microcosms/7/"', form)
        self.assertIn('<button type="submit" class="btn btn-link p-0 align-baseline">Mark everything read</button>', form)
        self.assertIn('>Ignore</button>', html)
        self.assertNotIn('metabar-admin-actions', html)
        self.assertNotIn('edit-microcosm', html)

    def test_admin_controls(self):
        html = self.render('microcosm.html', user=make_user(), permissions={'admin': True})
        self.assertIn('id="create_microcosm"', html)
        self.assertIn('<select id="metabar-admin-actions" class="form-select form-select-sm w-auto"', html)
        self.assertIn('<option value="move">Move</option>', html)
        self.assertIn('id="edit-microcosm"', html)

    def test_closed_forum(self):
        self.content.meta.flags['open'] = False
        html = self.render('microcosm.html', user=make_user())
        self.assertIn('This forum is closed and is not accepting new posts.', html)
        self.assertNotIn('create_conversation', html)

    # microcosms.html (the Site's home) ------------------------------------------

    def test_home_metabar(self):
        html = self.render('microcosms.html', user=make_user())
        self.assert_bootstrap_5_only(html)
        self.assertIn('<li><a href="/profiles/?top=true">People</a> <span>71,254</span></li>', html)
        self.assertIn('upcoming events', html)
        self.assertIn('Mark everything read', html)
        # Plain members get no posting buttons on the home page.
        self.assertNotIn('create_conversation', html)

    def test_home_admin_buttons(self):
        html = self.render('microcosms.html', user=make_user(), permissions={'admin': True})
        self.assertIn('id="create_conversation"', html)
        self.assertIn('id="create_microcosm"', html)
        self.assertIn('Manage site permissions', html)

    def test_breadcrumbs(self):
        html = self.render('breadcrumbs.html', skipself=False)
        self.assertIn('<li class="breadcrumb-item"><a href="/">Home</a></li>', html)
        self.assertIn('<li class="breadcrumb-item"><a href="/microcosms/7/">Rides</a></li>', html)
