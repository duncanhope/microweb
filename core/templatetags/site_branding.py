"""Site branding values turned into what the Bootstrap 5 base's CSS reads.

    {% load site_branding %}
    --bs-link-color-rgb: {{ site.link_color|rgb_triple }};
    <body class="{{ site.background_position|background_class }}">

Bootstrap 5 colours links with rgba(var(--bs-link-color-rgb), ...), so a
Site's hex link colour has to arrive as an "r, g, b" triple. It is computed
here, per request, because the colour comes from the API.

Light mode only: the Site's exact colour, as today. Adjusting it for
contrast in dark mode is the Color mode toggle's job (BS5-06).
"""
import re

from django import template

register = template.Library()

_HEX = re.compile(r'^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


@register.filter
def rgb_triple(colour):
    """'#4082c3' or '#48a' -> '64, 130, 195'. Anything that is not a 3 or 6
    digit hex colour gives '', so the template can fall back to the default."""
    match = _HEX.match((colour or '').strip())
    if not match:
        return ''
    digits = match.group(1)
    if len(digits) == 3:
        digits = ''.join(c * 2 for c in digits)
    return ', '.join(str(int(digits[i:i + 2], 16)) for i in (0, 2, 4))


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
