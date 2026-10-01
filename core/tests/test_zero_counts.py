"""Counts the API leaves out when they are zero. A message row said
"0 comment" because Huddle.from_summary set total_comments only when it was
non-zero, and the Bootstrap 3 event header said "/12" for an event with a
limit and no one going, because Event.from_summary did the same with
rsvp_attend. Both now default to 0."""
import re

from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Event, Huddle
from core.tests import test_event_rsvp
from core.tests.test_bs5_base import make_site
from core.tests.test_bs5_huddles import huddle_data


def huddle(total_comments=None):
    data = huddle_data()
    data.pop('totalComments')
    if total_comments is not None:
        data['totalComments'] = total_comments
    return Huddle.from_summary(data)


class HuddleCommentCountTests(SimpleTestCase):

    def test_total_comments_defaults_to_zero(self):
        self.assertEqual(huddle().total_comments, 0)
        self.assertEqual(huddle(0).total_comments, 0)
        self.assertEqual(huddle(5).total_comments, 5)

    def stat(self, engine, total):
        html = engines[engine].get_template('block_huddle.html').render(
            {'item': huddle(total), 'site': make_site()}, RequestFactory().get('/huddles/'))
        return re.sub(r'\s+', ' ', re.search(r'<span stat=.*?comments?\b', html, re.S).group(0))

    def test_both_rows_pluralise(self):
        for engine in ('django', 'bs5'):
            for total, text in ((None, '0</span> comments'), (0, '0</span> comments'), (1, '1</span> comment'),
                                (2, '2</span> comments'), (1200, '1,200</span> comments')):
                with self.subTest(engine=engine, total=total):
                    stat = self.stat(engine, total)
                    self.assertTrue(stat.endswith(text), stat)
                    self.assertIn('stat="%d"' % (total or 0), stat)


class EventAttendCountTests(SimpleTestCase):
    """The places taken on an event with a limit and no one going."""
    setUp = test_event_rsvp.EventRsvpTests.setUp
    page = test_event_rsvp.EventRsvpTests.page

    def test_rsvp_attend_defaults_to_zero(self):
        data = test_event_rsvp.load('event_with_comment.json')
        data.pop('rsvpAttend', None)
        self.assertEqual(Event.from_summary(data).rsvp_attend, 0)

    def test_no_one_going_is_zero_places_taken(self):
        self.event.update(rsvpLimit=12, rsvpSpaces=12)
        self.event.pop('rsvpAttend', None)
        for bs in (3, 5):
            for large in (False, True):
                with self.subTest(bs=bs, large=large):
                    html = self.page(bs, large)
                    self.assertNotRegex(html, r'>\s*/12')
                    # The large headers show the places only once someone is going or invited.
                    if not large:
                        self.assertRegex(html, r'>\s*0/12\s*</strong>')
