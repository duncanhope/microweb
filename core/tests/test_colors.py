from django.test import SimpleTestCase

from core import colors


class ParseHexTests(SimpleTestCase):

    def test_six_and_three_digit_hex(self):
        self.assertEqual(colors.parse_hex('#4082c3'), (64, 130, 195))
        self.assertEqual(colors.parse_hex('4898AC'), (72, 152, 172))
        self.assertEqual(colors.parse_hex('#48a'), (68, 136, 170))
        self.assertEqual(colors.parse_hex(' #ffffff '), (255, 255, 255))

    def test_anything_else_is_none(self):
        for value in (None, '', 'blue', '#12345', 'rgb(1, 2, 3)', '#4082c3; color: red'):
            with self.subTest(value=value):
                self.assertIsNone(colors.parse_hex(value))

    def test_triple(self):
        self.assertEqual(colors.triple((64, 130, 195)), '64, 130, 195')


class ContrastTests(SimpleTestCase):

    def test_known_ratios(self):
        self.assertAlmostEqual(colors.contrast(colors.WHITE, colors.BLACK), 21)
        self.assertAlmostEqual(colors.contrast((119, 119, 119), colors.WHITE), 4.48, places=2)
        self.assertEqual(colors.contrast((1, 2, 3), (1, 2, 3)), 1)

    def test_order_does_not_matter(self):
        self.assertEqual(colors.contrast((64, 130, 195), colors.DARK_BODY_BG),
                         colors.contrast(colors.DARK_BODY_BG, (64, 130, 195)))

    def test_dark_body_background_is_bootstraps(self):
        self.assertEqual(colors.DARK_BODY_BG, colors.parse_hex('#212529'))


class DarkLinkColourTests(SimpleTestCase):
    """The Site link colour in the dark Color mode reaches WCAG AA."""

    def assert_readable(self, rgb):
        self.assertGreaterEqual(colors.contrast(rgb, colors.DARK_BODY_BG), colors.AA)

    def test_wwcc_dark_grey_is_lightened_to_aa(self):
        link, hover = colors.dark_link_colours('#21201b')
        self.assertLess(colors.contrast(colors.parse_hex('#21201b'), colors.DARK_BODY_BG), 1.1)
        self.assert_readable(link)
        self.assertEqual(link, (140, 139, 136))
        self.assert_readable(hover)

    def test_readable_colour_is_unchanged(self):
        self.assert_readable(colors.parse_hex('#51a9ff'))
        link, hover = colors.dark_link_colours('#51a9ff')
        self.assertEqual(link, (81, 169, 255))
        self.assert_readable(hover)

    def test_mid_blue_is_lightened_just_enough(self):
        link, hover = colors.dark_link_colours('#1e72c4')
        self.assert_readable(link)
        self.assertEqual(link, (77, 144, 208))
        # One percent less tint would not reach AA: the adjustment is minimal.
        self.assertLess(colors.contrast(colors.mix((30, 114, 196), colors.WHITE, .19), colors.DARK_BODY_BG),
                        colors.AA)
        self.assert_readable(hover)

    def test_hover_is_a_lighter_step_on_dark(self):
        for colour in ('#21201b', '#51a9ff', '#1e72c4', '#4082c3', '#280fc2'):
            with self.subTest(colour=colour):
                link, hover = colors.dark_link_colours(colour)
                self.assertEqual(hover, colors.mix(link, colors.WHITE, colors.HOVER_STEP))
                self.assertGreater(colors.contrast(hover, colors.DARK_BODY_BG),
                                   colors.contrast(link, colors.DARK_BODY_BG))

    def test_darkens_on_a_background_white_cannot_reach(self):
        light_bg = (250, 250, 250)
        adjusted = colors.readable((200, 220, 255), light_bg)
        self.assertGreaterEqual(colors.contrast(adjusted, light_bg), colors.AA)
        self.assertLess(colors.luminance(adjusted), colors.luminance((200, 220, 255)))
        self.assertLess(colors.luminance(colors.hover(adjusted, light_bg)), colors.luminance(adjusted))

    def test_not_a_colour(self):
        self.assertIsNone(colors.dark_link_colours(''))
        self.assertIsNone(colors.dark_link_colours(None))

    def test_dark_links_reach_aa_on_the_body_and_the_metabar(self):
        # (link, surround): lfgss, wwcc on its blue surround, outliers, a black surround.
        for colour, surround in (('#1e72c4', '#424143'), ('#21201b', '#2c7ede'),
                                 ('#280fc2', '#171919'), ('#51a9ff', '#000000')):
            with self.subTest(colour=colour, surround=surround):
                panel = colors.dark_panel(colors.parse_hex(surround))
                for rgb in colors.dark_link_colours(colour, surround):
                    self.assertGreaterEqual(colors.contrast(rgb, colors.DARK_BODY_BG), colors.AA)
                    self.assertGreaterEqual(colors.contrast(rgb, panel), colors.AA)

    def test_dark_panel_is_the_body_at_panel_opacity_over_the_surround(self):
        self.assertEqual(colors.dark_panel((0, 0, 0)), colors.mix((0, 0, 0), colors.DARK_BODY_BG, .8))

    def test_unusable_surround_falls_back_to_the_body_only(self):
        self.assertEqual(colors.dark_link_colours('#21201b', ''), colors.dark_link_colours('#21201b'))
        self.assertEqual(colors.dark_link_colours('#21201b', 'none'), colors.dark_link_colours('#21201b'))
