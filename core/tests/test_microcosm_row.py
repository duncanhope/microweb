from types import SimpleNamespace

from django.template import engines
from django.test import SimpleTestCase


def forum(id, title, breadcrumb=None, parent=None):
    links = SimpleNamespace(parent=parent) if parent else SimpleNamespace()
    return SimpleNamespace(item_type='microcosm', item=SimpleNamespace(
        id=id, title=title, description='', logoUrl='', total_items=0, total_comments=0,
        most_recent_update=None, breadcrumb=breadcrumb,
        meta=SimpleNamespace(flags=SimpleNamespace(unread=False), links=links)))


def breadcrumb(*titles):
    return SimpleNamespace(breadcrumb={t: {'href': '/microcosms/%d/' % i, 'title': t} for i, t in enumerate(titles)})


class MicrocosmRowForumTests(SimpleTestCase):
    """Search results render conversation rows before forum rows in one
    context, so a forum row must not pick up the previous row's `item`."""

    def render(self, row, **context):
        template = engines['django'].from_string('{% load microcosm %}{% microcosm row showForum=True %}')
        return template.render({'row': row, **context})

    def test_forum_row_ignores_the_previous_rows_breadcrumb(self):
        previous = SimpleNamespace(breadcrumb=breadcrumb('Bikes & Bits'))
        html = self.render(forum(1, 'Wheels'), item=previous)
        self.assertNotIn('Bikes &amp; Bits', html)
        self.assertNotIn('Bikes & Bits', html)

    def test_forum_row_shows_its_own_breadcrumb(self):
        html = self.render(forum(1, 'Wheels', breadcrumb=breadcrumb('Home', 'Components')))
        self.assertIn('Components', html)

    def test_parent_shows_once_when_there_is_a_breadcrumb(self):
        parent = {'href': '/microcosms/2/', 'title': 'Components'}
        html = self.render(forum(1, 'Wheels', breadcrumb=breadcrumb('Home', 'Components'), parent=parent))
        self.assertEqual(html.count('Components'), 1)

    def test_parent_shows_without_a_breadcrumb(self):
        parent = {'href': '/microcosms/2/', 'title': 'Components'}
        self.assertIn('Components', self.render(forum(1, 'Wheels', parent=parent)))
