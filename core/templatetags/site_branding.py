"""Site branding values turned into what the Bootstrap 5 base's CSS reads.

    {% load site_branding %}
    --bs-link-color-rgb: {{ site.link_color|rgb_triple }};
    {% with dark=site.link_color|dark_link:site.background_color %}{{ dark.0 }} {{ dark.1 }}{% endwith %}
    <body class="{{ site.background_position|background_class }}">

Bootstrap 5 colours links with rgba(var(--bs-link-color-rgb), ...), so a
Site's hex link colour has to arrive as an "r, g, b" triple. It is computed
here, per request, because the colour comes from the API.

The light Color mode uses the Site's exact colour, as today. The dark one
uses the colour adjusted to WCAG AA against the dark body and the dark
metabar over the Site surround, and a hover shade derived from it (the maths
is in core/colors.py).
"""
from django import template

from core import colors

register = template.Library()


@register.filter
def rgb_triple(colour):
    """'#4082c3' or '#48a' -> '64, 130, 195'. Anything that is not a 3 or 6
    digit hex colour gives '', so the template can fall back to the default."""
    rgb = colors.parse_hex(colour)
    return colors.triple(rgb) if rgb else ''


@register.filter
def dark_link(colour, surround=None):
    """(link, hover) triples for the dark Color mode, or ('', ''). `surround` is
    the Site's background colour, which shows through the metabar panel."""
    pair = colors.dark_link_colours(colour, surround)
    return tuple(colors.triple(rgb) for rgb in pair) if pair else ('', '')


BACKGROUND_CLASSES = {
    'tile': 'mw-bg-tile',
    'cover': 'mw-bg-cover',
    'tall': 'mw-bg-tall',
    'wide': 'mw-bg-wide',
}


@register.filter
def background_class(position):
    """The body class for a Site's background image position mode (rules in
    _base.scss). Any other value, such as 'left' or 'center', pins the image
    to the top at that position: mw-bg-top."""
    return BACKGROUND_CLASSES.get(position, 'mw-bg-top')
