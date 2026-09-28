from django.template import Context, Template, TemplateSyntaxError
from django.test import SimpleTestCase

from core.templatetags.icon import ICON_DIR


def render(source):
    return Template('{% load icon %}' + source).render(Context())


class IconTagTests(SimpleTestCase):

    def test_decorative_by_default(self):
        svg = render('{% icon "search" %}')
        self.assertTrue(svg.startswith('<svg '))
        self.assertTrue(svg.endswith('</svg>'))
        self.assertIn('aria-hidden="true" focusable="false"', svg)
        self.assertIn('width="1em" height="1em"', svg)
        self.assertIn('fill="currentColor"', svg)
        self.assertIn('class="bi bi-search"', svg)
        self.assertIn('viewBox="0 0 16 16"', svg)
        self.assertIn('<path d="M11.742', svg)
        self.assertNotIn('role=', svg)
        self.assertNotIn('\n', svg)

    def test_label_makes_it_an_image_with_a_name(self):
        svg = render('{% icon "lock" label="Closed <conversation>" %}')
        self.assertIn('role="img" aria-label="Closed &lt;conversation&gt;"', svg)
        self.assertNotIn('aria-hidden', svg)
        self.assertNotIn('focusable', svg)

    def test_class_is_appended(self):
        svg = render('{% icon "pencil" class="text-muted me-1" %}')
        self.assertIn('class="bi bi-pencil text-muted me-1"', svg)

    def test_variables_are_resolved(self):
        svg = Template('{% load icon %}{% icon name label=text %}').render(
            Context({'name': 'reply', 'text': 'Reply'}))
        self.assertIn('class="bi bi-reply"', svg)
        self.assertIn('aria-label="Reply"', svg)

    def test_unknown_name_raises(self):
        with self.assertRaisesMessage(TemplateSyntaxError, "Unknown icon 'no-such-icon'"):
            render('{% icon "no-such-icon" %}')

    def test_path_traversal_is_an_unknown_name(self):
        with self.assertRaisesMessage(TemplateSyntaxError, 'Unknown icon'):
            render('{% icon "../bootstrap-icons/search" %}')

    def test_unknown_argument_raises(self):
        with self.assertRaisesMessage(TemplateSyntaxError, 'takes only label= and class='):
            render('{% icon "search" size="2" %}')

    def test_every_vendored_icon_renders(self):
        names = sorted(path.stem for path in ICON_DIR.glob('*.svg'))
        self.assertGreaterEqual(len(names), 26)
        for name in names:
            with self.subTest(name=name):
                self.assertIn('class="bi bi-%s"' % name, render('{%% icon "%s" %%}' % name))
