from django.test import RequestFactory
from django.test import SimpleTestCase
from django.test import override_settings

from search.views import _parse_offset


@override_settings(PAGE_SIZE=25)
class SearchOffsetTests(SimpleTestCase):
    """A bad ?offset= is read as the first page, not answered with an error."""

    def offset(self, query):
        return _parse_offset(RequestFactory().get('/search/' + query))

    def test_invalid_offset_is_the_first_page(self):
        for offset in (
            '%27%3E%3Casdf%20alt%3D%22%22%3E-f3f3',
            '%2527%253E%253Casdf%2520alt%253D%2522%2522%253E-f3f3',
        ):
            with self.subTest(offset=offset):
                self.assertEqual(self.offset('?offset=%s' % offset), 0)

    def test_negative_offset_is_the_first_page(self):
        self.assertEqual(self.offset('?offset=-1'), 0)

    def test_missing_offset_is_the_first_page(self):
        self.assertEqual(self.offset(''), 0)

    def test_offset_is_rounded_down_to_a_page(self):
        self.assertEqual(self.offset('?offset=60'), 50)
