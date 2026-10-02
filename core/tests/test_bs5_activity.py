"""The activity lists family on Bootstrap 5 (BS5-10): updates.html (Following),
today.html, trending.html, search.html, watchers.html and block_huddle.html,
with the comment rows of block_list_comments.html (BS5-09), search.js and
the _activity.scss partial."""
import copy
import json
import os
import re
from pathlib import Path

from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Search, Trending, UpdateList, WatcherList
from core.tests.test_bs5_base import make_site, make_user

REPO = Path(settings.PROJECT_ROOT).parent
DATA = Path(__file__).resolve().parent / 'data'
PARTIAL = REPO / 'core' / 'static' / 'themes' / '1' / 'scss' / '_activity.scss'
SCRIPTS = REPO / 'core' / 'static' / 'js' / 'bs5'

# Every template the family owns in core/templates_bs5/.
FAMILY = ['updates.html', 'watchers.html', 'today.html', 'trending.html', 'search.html', 'block_huddle.html']
FAMILY_SCRIPTS = ['search.js']

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')

PAGE = {'total': 2, 'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1, 'page': 1, 'links': [], 'type': ''}
META = {'flags': {}, 'links': []}


def load(name):
    with open(DATA / name) as f:
        return json.load(f)['data']


def conversation():
    return copy.deepcopy(load('microcosm_with_items.json')['items']['items'][1]['item'])


def forum():
    return copy.deepcopy(load('microcosm_with_items.json')['items']['items'][0]['item'])


def comment():
    return copy.deepcopy(load('conversation_with_paginated_comments.json')['comments']['items'][0])


def huddle(participants=2):
    people = [{'id': 20 + n, 'profileName': 'p%d' % n, 'avatar': ''} for n in range(participants)]
    return {'id': 3310071, 'title': 'bs5 testing', 'totalComments': 2, 'participants': people,
            'lastCommentId': 77, 'lastCommentCreated': '2026-09-29T12:00:00Z', 'lastCommentCreatedBy': people[0],
            'meta': {'created': '2026-09-28T12:00:00Z', 'createdBy': people[0], 'flags': {'unread': True},
                     'links': [{'rel': 'self', 'href': '/api/v1/huddles/3310071'}]}}


def updates(*items):
    return UpdateList({'updates': dict(PAGE, items=list(items)), 'meta': META})


def update(item_type, item, update_type='new_comment', unread=False, **extra):
    data = {'id': 1, 'updateType': update_type, 'itemType': item_type, 'item': item,
            'meta': {'flags': {'unread': unread}, 'links': [], 'created': '2026-09-29T12:00:00Z'}}
    data.update(extra)
    return data


def search(results=None, **query):
    data = {'query': query, 'timeTakenInMs': 567}
    if results is not None:
        data['results'] = dict(PAGE, total=len(results), items=results)
    return Search.from_api_response(data)


def result(item_type, item, **extra):
    data = {'itemType': item_type, 'item': item, 'rank': 1, 'lastModified': '2026-09-29T12:00:00Z',
            'highlight': '', 'unread': False}
    data.update(extra)
    return data


def huddle_item(participants=2):
    return search([result('huddle', huddle(participants))]).results.items[0].item


class Bs5ActivityTests(SimpleTestCase):

    def render(self, name, user=None, path='/', **extra):
        request = RequestFactory().get(path)
        context = {'site': make_site(), 'user': user}
        context.update(extra)
        return engines['bs5'].get_template(name).render(context, request)

    def render_search(self, user=None, **extra):
        extra.setdefault('content', search([result('conversation', conversation())], q='bike', inTitle=True,
                                           sort='date'))
        return self.render('search.html', user=user, path='/search/?q=bike&defaults=true', **extra)

    def assert_bootstrap_5_only(self, html):
        self.assertNotIn('data-toggle=', html)
        self.assertNotIn('data-target=', html)
        self.assertNotIn('data-dismiss=', html)
        self.assertNotIn('sprite-', html)
        self.assertNotIn('glyphicon', html)
        self.assertNotIn('$(', html)

    def test_every_family_template_is_served_from_the_bs5_tree(self):
        for name in FAMILY:
            with self.subTest(template=name):
                origin = engines['bs5'].get_template(name).origin.name
                self.assertEqual(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR), name)

    def test_every_family_template_renders_without_bootstrap_3_or_jquery(self):
        content = {
            'updates.html': updates(update('conversation', conversation()), update('huddle', huddle())),
            'watchers.html': WatcherList({'watchers': dict(PAGE, items=[])}),
            'today.html': search([result('conversation', conversation()), result('huddle', huddle())]),
            'trending.html': Trending.from_api_response({'items': dict(PAGE, items=[result('conversation', conversation())])}),
            'search.html': search([result('microcosm', forum()), result('comment', comment(), parentItemType='conversation',
                                                                      parentItem=conversation())], q='bike'),
        }
        for name in FAMILY:
            for user in (None, make_user()):
                with self.subTest(template=name, member=bool(user)):
                    extra = {'item': huddle_item()} if name == 'block_huddle.html' else {'content': content[name]}
                    self.assert_bootstrap_5_only(self.render(name, user=user, **extra))

    def test_partial_has_no_colour_literals(self):
        self.assertEqual(COLOUR_LITERAL.findall(PARTIAL.read_text()), [])
        self.assertIn('@import "activity";', (PARTIAL.parent / 'site.scss').read_text())

    def test_scripts_are_modules_without_jquery(self):
        for name in FAMILY_SCRIPTS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text()
                code = re.sub(r'(?m)^\s*//.*$', '', source)
                self.assertIsNone(re.search(r'\$\(|\$\.|jQuery', code))
                self.assertRegex(source, r'(?m)^(import|export) ')

    # updates.html ---------------------------------------------------------------

    def test_following_as_a_guest(self):
        html = self.render('updates.html', path='/updates/')
        self.assertIn('<h1 class="mw-list-title"><a href="/updates/">Following</a></h1>', html)
        self.assertIn('Please sign in to view updates on the items that you are following.', html)
        self.assertNotIn('mw-rows', html)
        self.assertNotIn('Update notification settings', html)

    def test_following_with_nothing_to_show(self):
        html = self.render('updates.html', user=make_user(), content=updates())
        self.assertIn('No updates to show.', html)
        self.assertIn('<a href="/updates/settings/" class="btn mw-btn">', html)

    def test_following_rows(self):
        reply = update('comment', comment(), update_type='reply_to_comment', parentItemType='conversation',
                       parentItem=conversation())
        html = self.render('updates.html', user=make_user(), content=updates(
            update('conversation', conversation(), unread=True),
            update('comment', comment(), parentItemType='conversation', parentItem=conversation()),
            update('huddle', huddle()),
            reply,
        ))
        self.assertEqual(html.count('<li class="mw-row'), 4)
        # A new comment on a conversation is that conversation's row, in its forum.
        self.assertEqual(html.count('<a href="/conversations/100/newest/" itemprop="url">Pinned and closed</a>'), 2)
        self.assertIn('in <a href="/microcosms/7/">Rides</a>', html)
        self.assertIn('<span class="badge text-bg-warning">NEW</span>', html)
        # A message row.
        self.assertIn('<a href="/huddles/3310071/newest/">bs5 testing</a>', html)
        # A reply is a comment row naming who replied.
        self.assertIn('replied to your comment</p>', html)
        self.assertIn('class="mw-prose mw-excerpt-text"', html)

    # block_huddle.html ----------------------------------------------------------------

    def test_message_row_shows_six_participants_and_the_rest_as_a_count(self):
        html = self.render('block_huddle.html', user=make_user(), item=huddle_item(participants=8), unread=True)
        self.assertEqual(html.count('data-bs-toggle="tooltip" title="@p'), 6)
        self.assertIn('<li class="list-inline-item">+2</li>', html)
        self.assertIn('role="img" aria-label="Message"', html)
        self.assertIn('<span class="badge text-bg-warning">NEW</span>', html)
        self.assertIn('<a href="/comments/77/incontext/">replied</a>', html)

    # today.html -------------------------------------------------------------------

    def test_today(self):
        content = search([result('conversation', conversation()), result('huddle', huddle())])
        html = self.render('today.html', content=content, path='/today/')
        # A link to the page itself, like the Following and People headings.
        self.assertIn('<h1 class="mw-list-title"><a href="/today/">Today on LFGSS</a></h1>', html)
        self.assertEqual(html.count('<li class="mw-row'), 2)
        self.assertNotIn('data-mw-filters', html, 'guests get no filters')
        self.assertNotIn('filters.js', html)

    def test_today_following_filter(self):
        html = self.render('today.html', user=make_user(), content=search([], following=True), path='/today/')
        self.assertIn('The forum has been quiet today.', html)
        self.assertIn('<form action="/today/" method="GET" class="mw-filters mw-options" data-mw-filters>', html)
        self.assertIn('name="following" value="true" checked>', html)
        self.assertIn('<script type="module" src="/static/js/bs5/filters.js">', html)

    # trending.html ----------------------------------------------------------------

    def test_trending(self):
        content = Trending.from_api_response({'items': dict(PAGE, items=[
            result('conversation', conversation()), result('event', dict(load('event_without_comment.json'), totalComments=0, totalViews=3))])})
        html = self.render('trending.html', content=content, path='/trending/')
        self.assertIn('<h1 class="mw-list-title"><a href="/trending/">Trending</a></h1>', html)
        self.assertEqual(html.count('<li class="mw-row'), 2)
        self.assertIn('itemtype="http://schema.org/Event"', html)
        html = self.render('trending.html', content=Trending.from_api_response({}), path='/trending/')
        self.assertIn('Nothing is trending right now.', html)

    # search.html ------------------------------------------------------------------

    def test_search_results(self):
        html = self.render_search()
        self.assertIn('<h1 class="mw-list-title">Search results for: bike</h1>', html)
        self.assertIn('<p class="mw-search-stats">1 matches. Search took 0.567 seconds.</p>', html)
        self.assertEqual(html.count('<li class="mw-row'), 1)
        self.assertIn('<script type="module" src="/static/js/bs5/search.js">', html)

    def test_search_options_carry_every_filter(self):
        html = self.render_search()
        self.assertIn('<form action="/search/" method="GET" class="mw-filters mw-options" data-mw-filters>', html)
        self.assertIn('<input type="hidden" name="q" value="bike">', html)
        self.assertIn('name="inTitle" value="true" checked>', html)
        self.assertIn('name="sort" value="date" checked>', html)
        self.assertIn('name="sort" value="">', html)
        self.assertIn('name="type" value="conversation">', html)
        self.assertNotIn('name="type" value="huddle"', html, 'guests cannot search messages')
        self.assertNotIn('name="following"', html)
        html = self.render_search(user=make_user())
        self.assertIn('name="type" value="huddle">', html)
        self.assertIn('name="following" value="true">', html)

    def test_search_for_events(self):
        content = search([], type=['event'], eventAfter='0', sort='oldest')
        html = self.render_search(content=content, user=make_user())
        self.assertIn("We couldn't find any items that matched your search.", html)
        self.assertIn('>Popular Searches</h2>', html)
        self.assertIn('href="/search?type=event&amp;eventAfter=0&amp;sort=oldest"', html)
        self.assertIn('name="type" value="event" checked>', html)
        self.assertIn('name="eventAfter" value="0" checked>', html)
        self.assertIn('name="sort" value="oldest" checked>', html)
        self.assertNotIn('Relevancy', html, 'no words, no relevancy')

    def test_search_without_words(self):
        html = self.render_search(content=search())
        self.assertIn('No valid search terms supplied.', html)
        self.assertNotIn('Popular Searches', html)

    def test_forum_rows_show_their_own_trail(self):
        """A forum row after a conversation row names its own parents, not the conversation's forum."""
        own = forum()
        own['breadcrumb'] = [{'rel': 'microcosm', 'level': 1, 'href': '/api/v1/microcosms/2', 'title': 'Classifieds'}]
        own['meta']['links'].append({'rel': 'parent', 'href': '/api/v1/microcosms/2', 'title': 'Classifieds'})
        leaky = conversation()
        leaky['breadcrumb'] = [{'rel': 'microcosm', 'level': 1, 'href': '/api/v1/microcosms/7', 'title': 'Leaky'}]
        content = search([result('conversation', leaky), result('microcosm', own), result('microcosm', forum())],
                         q='bike')
        html = self.render_search(content=content)
        self.assertEqual(html.count('>Leaky</a>'), 1, 'the conversation\'s trail leaked into a forum row')
        self.assertEqual(html.count('>Classifieds</a>'), 1, 'the trail and the parent both name the parent')

    # watchers.html ----------------------------------------------------------------

    def test_watchers_form_keeps_the_views_field_names(self):
        watcher = {'id': 3435240, 'itemTypeId': 6, 'itemType': 'conversation', 'itemId': 406745,
                   'sendEmail': True, 'sendSMS': False, 'item': conversation()}
        html = self.render('watchers.html', user=make_user(), content=WatcherList({'watchers': dict(PAGE, items=[watcher])}))
        self.assertIn('<input type="hidden" name="watcher_id" value="3435240">', html)
        self.assertIn('name="send_email_3435240" type="checkbox" aria-label="Send me an email" checked>', html)
        self.assertIn('name="delete_watcher_3435240" type="checkbox" aria-label="Stop following">', html)
        self.assertIn('<a href="/conversations/406745/newest/">Pinned and closed</a>', html)
        html = self.render('watchers.html', user=make_user(), content=WatcherList({'watchers': dict(PAGE, items=[])}))
        self.assertIn("you'll start watching it", html)
