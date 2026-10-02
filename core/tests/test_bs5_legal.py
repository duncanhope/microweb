"""The legal and error pages on Bootstrap 5 (BS5-15): legal.html, legals.html,
403.html, 404.html and 500.html, with the _legal.scss partial. The family
has no scripts of its own.

The error pages are rendered the way core/views.py ErrorView renders them,
including with the API unreachable: the 500 page in particular must render
whatever failed, as the Bootstrap 3 one does.

Every Site, person and document here is made up."""
import os
import re
from pathlib import Path
from unittest import mock

import requests
from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core import views
from core.api.exceptions import APIException
from core.api.resources import Legal, Site, WhoAmI
from core.tests.test_bs5_base import make_site, make_user
from core.tests.test_edit_reason import SITE_URL, WHOAMI_URL, load, request

REPO = Path(settings.PROJECT_ROOT).parent
PARTIAL = REPO / 'core' / 'static' / 'themes' / '1' / 'scss' / '_legal.scss'

FAMILY = ['legal.html', 'legals.html', '403.html', '404.html', '500.html']

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')

# A made-up policy with what the real ones hold: headings, a nested list, and
# a table whose cells hold ol[type=a] with ol[type=i] inside.
DOCUMENT = '''<h2>A made-up forum</h2>
<h2>Forum Terms of Use</h2>
<h3>Welcome</h3>
<p>Be <strong>kind</strong>.</p>
<ul><li>One<ul><li>One and a half</li></ul></li></ul>
<table>
	<tr><th>No.</th><th>Kind</th><th>Offences</th></tr>
	<tr><td>1.</td><td>Made up</td><td><ol type="a"><li>First:<ol type="i"><li>inner</li></ol></li><li>Second</li></ol></td></tr>
</table>'''

API_HOST = 'madeup.microcosm.app'


def banned_user():
    user = make_user()
    user.meta.permissions = {'banned': True}
    return user


class Bs5LegalTests(SimpleTestCase):

    def render(self, name, **context):
        context.setdefault('site', make_site())
        return engines['bs5'].get_template(name).render(context, RequestFactory().get('/about/'))

    def assert_bootstrap_5_only(self, html):
        self.assertIn('bs5.min.css', html)
        for old in ('data-toggle=', 'data-target=', 'data-dismiss=', 'sprite-', 'glyphicon', '$(', 'row-meta',
                    'content-header', 'metabar-module', 'comment-item-body', 'href="#"'):
            self.assertNotIn(old, html)

    def main(self, html):
        return html[html.index('<main'):html.index('</main>')]

    # The family ---------------------------------------------------------------------

    def test_every_family_template_is_served_from_the_bs5_tree(self):
        for name in FAMILY:
            with self.subTest(template=name):
                origin = engines['bs5'].get_template(name).origin.name
                self.assertEqual(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR), name)

    def test_every_page_renders_without_bootstrap_3_or_jquery(self):
        pages = {
            'legal.html': dict(content=Legal.from_api_response({'html': DOCUMENT}), page_section='terms', site_section='legal'),
            'legals.html': dict(site_section='legal'),
            '403.html': dict(user=make_user()),
            '404.html': {},
            '500.html': dict(detail='Made up'),
        }
        for name, context in pages.items():
            with self.subTest(template=name):
                self.assert_bootstrap_5_only(self.render(name, **context))
        self.assert_bootstrap_5_only(self.render('403.html', logout=True))

    def test_partial_has_no_colour_literals(self):
        self.assertEqual(COLOUR_LITERAL.findall(PARTIAL.read_text()), [])
        self.assertIn('@import "legal";', (PARTIAL.parent / 'site.scss').read_text())

    # The policies -------------------------------------------------------------------

    def test_a_policy(self):
        html = self.render('legal.html', content=Legal.from_api_response({'html': DOCUMENT}), page_section='terms',
                           site_section='legal')
        self.assertIn('<title>Terms of Use | About</title>', html)
        self.assertIn('<meta name="Description" content="This document describes the general terms of use of the'
                      ' forum.">', html)
        main = self.main(html)
        self.assertIn('<li class="breadcrumb-item"><a href="/about/">About</a></li>', main)
        self.assertIn('<h1 class="visually-hidden">Terms of Use</h1>', main)
        # The document is the API's HTML as it is, in the prose wrapper.
        self.assertIn('<div class="mw-prose mw-legal">\n\t' + DOCUMENT + '\n</div>', main)
        sidebar = html[html.index('<aside'):html.index('</aside>')]
        self.assertIn('<h2 class="mw-module-heading">Terms of Use</h2>', sidebar)

    def test_each_policy_names_itself(self):
        for section, title in (('privacy', 'Privacy Policy'), ('cookies', 'Cookie Policy')):
            with self.subTest(section=section):
                html = self.render('legal.html', content=Legal.from_api_response({'html': '<p>Made up</p>'}), page_section=section)
                self.assertIn('<title>%s | About</title>' % title, html)
                self.assertIn('<h1 class="visually-hidden">%s</h1>' % title, html)
                self.assertIn('<h2 class="mw-module-heading">%s</h2>' % title, html)

    def test_about(self):
        html = self.main(self.render('legals.html', site=make_site(title='Made up', description='<p>About us.</p>'),
                                     site_section='legal'))
        self.assertIn('<h1 class="mw-list-title mb-2">About</h1>', html)
        # The breadcrumb stops at Home: the page is not linked to itself.
        self.assertNotIn('<a href="/about/">', html)
        self.assertIn('<h2>Made up</h2>', html)
        # The description is HTML of its own, not wrapped in another paragraph.
        self.assertIn('<div><p>About us.</p></div>', html)
        for path, text in (('terms', 'Our terms of use'), ('privacy', 'Our privacy policy'),
                           ('cookies', 'Our use of cookies')):
            self.assertIn('<li><a href="/about/%s/">%s</a></li>' % (path, text), html)

    # The error pages -------------------------------------------------------------------

    def test_not_found(self):
        html = self.render('404.html')
        self.assertIn('<title>Not Found | LFGSS</title>', html)
        main = self.main(html)
        self.assertIn('<h1 class="mw-list-title">Not Found</h1>', main)
        self.assertIn('<a href="/">Click here to go back to the homepage</a>', main)

    def test_not_permitted(self):
        main = self.main(self.render('403.html', user=make_user()))
        self.assertIn('<h1 class="mw-list-title">Not permitted</h1>', main)
        self.assertIn("It looks like you don't have permission to do that.", main)
        self.assertIn('<a href="/">Click here to return to the home page</a>', main)

    def test_banned(self):
        main = self.main(self.render('403.html', user=banned_user()))
        self.assertIn('You have been banned from this site.', main)
        self.assertNotIn('permission', main)

    def test_logged_out(self):
        html = self.render('403.html', logout=True)
        self.assertIn('<title>Logged out | LFGSS</title>', html)
        main = self.main(html)
        self.assertIn('<h1 class="mw-list-title">Logged out</h1>', main)
        self.assertIn('<button type="button" class="btn btn-link" onclick="authSignin();">sign in again to'
                      ' continue</button>', main)
        # The base has no authSignout without a user: sign out posts its form.
        self.assertIn('<button type="submit" class="btn btn-link" form="signout-form">view the site as a'
                      ' guest</button>', main)
        self.assertIn('<form id="signout-form" class="d-none" method="POST" action="/logout/">', html)
        self.assertIn('function authSignin()', html)

    def test_server_error_gives_the_api_reason(self):
        main = self.main(self.render('500.html', detail='Too <b>many</b> results'))
        self.assertIn('<h1 class="mw-list-title">Server Error</h1>', main)
        self.assertIn('<p>The reason was: <em>Too &lt;b&gt;many&lt;/b&gt; results</em></p>', main)
        self.assertNotIn('The error has been logged', main)
        self.assertIn('<div hidden>\n\t::CLOUDFLARE_ERROR_500S_BOX::\n\t</div>', main)

    def test_server_error_with_an_empty_context(self):
        """No site, no user, no request attributes from ContextMiddleware: the
        page still renders on the Bootstrap 5 base."""
        html = engines['bs5'].get_template('500.html').render({}, RequestFactory().get('/'))
        self.assertIn('<title>Server Error | </title>', html)
        self.assertIn('bs5.min.css', html)
        self.assertIn('The error has been logged. Please try again later.', html)
        self.assertIn('id="login"', html)

    def test_bootstrap_3_pages_are_unchanged(self):
        html = engines['django'].get_template('500.html').render({}, RequestFactory().get('/'))
        self.assertIn('<p class="row-meta">The error has been logged. Please try again later.</p>', html)
        self.assertNotIn('bs5.min.css', html)


class Bs5ErrorViewTests(SimpleTestCase):
    """core/views.py ErrorView picks the Bootstrap 5 page for ?bs=5 and the bs
    cookie, as core/framework.py does for every page, and Bootstrap 3 otherwise."""

    def get(self, query='', cookies=None):
        req = RequestFactory().get('/missing/' + query, HTTP_HOST=API_HOST)
        req.COOKIES.update(cookies or {})
        return req

    def answered(self, req):
        """Run with made-up Site and whoami answers from the API."""
        site_url = Site.build_request(API_HOST)[0]
        whoami_url = WHOAMI_URL
        if 'access_token' in req.COOKIES:
            whoami_url = WhoAmI.build_request(API_HOST, req.COOKIES['access_token'])[0]
        answers = {site_url: load('site.json'), whoami_url: load('whoami.json')}
        # build_error_view_data reads each answer on its own: one stand-in
        # answer, read as all of them.
        return mock.patch.multiple(views, response_list_to_dict=mock.Mock(return_value=answers),
                                   fetch=mock.Mock(map=mock.Mock(return_value=[None])))

    def api_down(self):
        return mock.patch('requests.get', side_effect=requests.ConnectionError('made-up outage'))

    def is_bs5(self, response):
        return b'bs5.min.css' in response.content

    def test_each_error_page_follows_the_choice(self):
        pages = {'not_found': 404, 'forbidden': 403, 'server_error': 500, 'requires_login': 403}
        for name, status in pages.items():
            for query, cookies, bs5 in (('?bs=5', None, True), ('', {'bs': '5'}, True), ('', None, False),
                                        ('?bs=3', {'bs': '5'}, False)):
                with self.subTest(view=name, query=query, cookies=cookies):
                    req = self.get(query, cookies)
                    with self.answered(req):
                        response = getattr(views.ErrorView, name)(req)
                    self.assertEqual(response.status_code, status)
                    self.assertEqual(self.is_bs5(response), bs5)

    def test_signed_in_pages_show_the_member(self):
        req = self.get('?bs=5', {'access_token': 'made-up'})
        with self.answered(req):
            html = views.ErrorView.forbidden(req).content.decode()
        self.assertIn('<h1 class="mw-list-title">Not permitted</h1>', html)
        self.assertIn('id="profile"', html)
        self.assertIn('Frodo', html)
        self.assertIn('<title>Not permitted | Middle Earth</title>', html)

    def test_respond_with_error_shows_the_api_reason(self):
        req = self.get('?bs=5')
        error = APIException('Made up', 500, detail={'errorDetail': 'A made-up reason'})
        with self.answered(req):
            response = views.respond_with_error(req, error)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b'The reason was: <em>A made-up reason</em>', response.content)
        self.assertTrue(self.is_bs5(response))

    def test_every_error_page_renders_with_the_api_unreachable(self):
        """Every API call fails: the pages render with no Site and no member."""
        for name, status in (('server_error', 500), ('not_found', 404), ('forbidden', 403)):
            with self.subTest(view=name):
                req = self.get('?bs=5', {'access_token': 'made-up'})
                with self.api_down(), self.assertLogs('core.api.fetch', 'ERROR'):
                    response = getattr(views.ErrorView, name)(req)
                self.assertEqual(response.status_code, status)
                self.assertTrue(self.is_bs5(response))
                self.assertIn(b'<title>', response.content)
                self.assertNotIn(b'id="profile"', response.content)

    def test_server_error_on_a_custom_domain_with_the_api_unreachable(self):
        """The Site's address is cached, so only the Site lookup fails."""
        req = RequestFactory().get('/?bs=5', HTTP_HOST='forum.example.org')
        with self.api_down(), self.assertLogs('core.api.fetch', 'ERROR'), \
                mock.patch('core.api.resources.mc') as mc:
            mc.get.return_value = 'madeup.microcosm.app'
            response = views.ErrorView.server_error(req)
        self.assertEqual(response.status_code, 500)
        self.assertTrue(self.is_bs5(response))
        self.assertIn(b'Server Error', response.content)

    def test_server_error_for_an_unknown_host(self):
        req = RequestFactory().get('/?bs=5', HTTP_HOST='203.0.113.9')
        with mock.patch('core.api.resources.mc') as mc:
            mc.get.return_value = None
            response = views.ErrorView.server_error(req)
        self.assertEqual(response.status_code, 500)
        self.assertTrue(self.is_bs5(response))


class Bs5LegalViewTests(SimpleTestCase):
    """core/views.py LegalView through the view, on made-up answers."""

    def setUp(self):
        patch = mock.patch.object(views.Legal, 'build_request', return_value=('legal', {}, {}))
        patch.start()
        self.addCleanup(patch.stop)

    def page(self, view, path, *args):
        answers = {SITE_URL: load('site.json'), WHOAMI_URL: load('whoami.json'), 'legal': {'html': DOCUMENT}}
        with mock.patch.object(views.fetch, 'map', return_value=[]), \
                mock.patch.object(views, 'response_list_to_dict', return_value=answers):
            response = view(request(path), *args)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_a_policy(self):
        html = self.page(views.LegalView.single, '/about/terms/?bs=5', 'terms')
        self.assertIn('bs5.min.css', html)
        self.assertIn('<ol type="a"><li>First:<ol type="i"><li>inner</li></ol></li>', html)
        self.assertIn('<title>Terms of Use | About</title>', html)

    def test_about(self):
        html = self.page(views.LegalView.list, '/about/?bs=5')
        self.assertIn('bs5.min.css', html)
        self.assertIn('<h2>Middle Earth</h2>', html)

    def test_bootstrap_3_without_the_choice(self):
        html = self.page(views.LegalView.single, '/about/terms/', 'terms')
        self.assertNotIn('bs5.min.css', html)
        self.assertIn('<div class="content-body comment-item-body">', html)
