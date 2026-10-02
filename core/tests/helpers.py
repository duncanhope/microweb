"""Made-up Sites, members, requests and API answers shared by the tests.

Every Site, person, huddle and comment here is made up."""
import json
from pathlib import Path
from types import SimpleNamespace

from django.test import RequestFactory

DATA = Path(__file__).resolve().parent / 'data'
SITE_URL, WHOAMI_URL = 'site', 'whoami'
PAGE = {'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1, 'page': 1, 'links': []}


def load(name):
    """The data of a recorded API answer in core/tests/data/."""
    with open(DATA / name) as f:
        return json.load(f)['data']


def request(path, method='get', data=None):
    """A signed-in request as ContextMiddleware leaves it for a view."""
    request = getattr(RequestFactory(), method)(path, data or {})
    request.access_token = 'token'
    request.whoami_url = WHOAMI_URL
    request.site_url = SITE_URL
    request.view_requests = []
    request.color_mode = 'auto'
    return request


def make_site(**overrides):
    site = dict(
        title='LFGSS', description='A forum.', subdomain_key='lfgss', theme_id=1,
        logo_url='https://lfgss.microcosm.app/logo.png', link_color='#4082c3',
        background_color='#424143', background_url='', background_position='',
        site_url='https://www.lfgss.com', auth0_domain='buro9.eu.auth0.com', auth0_client_id='client',
        menu=[],
    )
    site.update(overrides)
    return SimpleNamespace(**site)


def make_user(unread=0):
    return SimpleNamespace(
        id=54446, profile_name='duncs', avatar='https://www.gravatar.com/avatar/x',
        meta=SimpleNamespace(stats={'unreadHuddles': unread}))


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
