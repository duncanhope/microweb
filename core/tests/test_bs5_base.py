from types import SimpleNamespace

from django.template import engines
from django.test import RequestFactory
from django.test import SimpleTestCase

from core.templatetags.site_branding import rgb_triple

PAGE = '{% extends "base.html" %}{% block content %}<p>page content</p>{% endblock %}' \
       '{% block sidebar %}<p>sidebar content</p>{% endblock %}'


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


class Bs5BaseTests(SimpleTestCase):
    """core/templates_bs5/base.html for guests and members."""

    def render(self, user=None, **site):
        request = RequestFactory().get('/about/terms/')
        template = engines['bs5'].from_string(PAGE)
        return template.render({'site': make_site(**site), 'user': user}, request)

    def assert_no_bootstrap_3_or_jquery(self, html):
        self.assertNotIn('data-toggle=', html)
        self.assertNotIn('data-target=', html)
        self.assertNotIn('data-dismiss=', html)
        self.assertNotIn('sprite-', html)
        self.assertNotIn('$(', html)

    def test_guest(self):
        html = self.render()
        self.assert_no_bootstrap_3_or_jquery(html)
        self.assertIn('data-bs-theme="light"', html)
        self.assertIn('page content', html)
        self.assertIn('sidebar content', html)
        self.assertIn('Browsing as <strong>guest</strong>', html)
        self.assertIn('id="modal-signin"', html)
        self.assertIn('class="btn-close', html)
        self.assertIn('lock-passwordless.min.js', html)
        self.assertIn("addEventListener('hidden.bs.modal'", html)
        self.assertNotIn('function authSignout', html)
        self.assertIn('data-bs-toggle="offcanvas" data-bs-target="#mw-menu"', html)
        self.assertIn('data-bs-toggle="offcanvas" data-bs-target="#mw-metabar"', html)
        self.assertIn('<script type="module" src="/static/js/bs5/base.js">', html)

    def test_member(self):
        html = self.render(user=make_user(unread=3))
        self.assert_no_bootstrap_3_or_jquery(html)
        self.assertNotIn('id="modal-signin"', html)
        self.assertNotIn('lock-passwordless', html)
        self.assertIn('function authSignout', html)
        self.assertIn('duncs', html)
        self.assertIn('/profiles/54446/edit/', html)
        self.assertIn('<span class="badge text-bg-warning">3 <svg', html)
        self.assertIn('aria-label="Sign out"', html)

    def test_member_without_unread_messages_has_no_badge(self):
        html = self.render(user=make_user(unread=0))
        self.assertNotIn('badge', html)
        self.assertIn('bi-envelope', html)

    def test_site_link_colour_reaches_bootstrap_variables(self):
        html = self.render(link_color='#4898AC')
        self.assertIn('--bs-link-color-rgb: 72, 152, 172;', html)
        self.assertIn('--bs-link-hover-color-rgb: 72, 152, 172;', html)
        self.assertIn('--bs-link-color: rgb(72, 152, 172);', html)

    def test_unusable_link_colour_keeps_bootstrap_default(self):
        html = self.render(link_color='')
        self.assertNotIn('--bs-link-color', html)

    def test_background_colour_and_position_modes(self):
        html = self.render()
        self.assertIn('--mw-site-bg-color: #424143;', html)
        self.assertNotIn('--mw-site-bg-image', html)
        self.assertIn('<body>', html)
        image = 'https://example.com/bg.jpg'
        for position, css_class in (('tile', 'mw-bg-tile'), ('cover', 'mw-bg-cover'), ('tall', 'mw-bg-tall'),
                                    ('wide', 'mw-bg-wide'), ('center', 'mw-bg-top'), ('left', 'mw-bg-top')):
            with self.subTest(position=position):
                html = self.render(background_url=image, background_position=position)
                self.assertIn('<body class="%s">' % css_class, html)
                self.assertIn("--mw-site-bg-image: url('%s');" % image, html)
                self.assertIn('--mw-site-bg-position: %s;' % position, html)


class RgbTripleTests(SimpleTestCase):

    def test_six_digit_hex(self):
        self.assertEqual(rgb_triple('#4082c3'), '64, 130, 195')
        self.assertEqual(rgb_triple('#4898AC'), '72, 152, 172')

    def test_three_digit_hex_and_no_hash(self):
        self.assertEqual(rgb_triple('#48a'), '68, 136, 170')
        self.assertEqual(rgb_triple('ffffff'), '255, 255, 255')

    def test_anything_else_is_empty(self):
        for value in (None, '', 'blue', '#12345', 'rgb(1, 2, 3)', '#4082c3; color: red'):
            with self.subTest(value=value):
                self.assertEqual(rgb_triple(value), '')
