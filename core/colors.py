"""Colour maths for Site branding under each Color mode (BS5-06).

A Site's link colour is used exactly in the light Color mode. In the dark
Color mode it is moved towards white (or towards black, if white cannot get
there) just far enough to reach WCAG AA contrast against every background a
link sits on: the dark body, and the metabar, where the translucent panel
lets the Site surround show through. So a dark link such as wwcc's #21201b
stays readable in both places. The hover colour is a further step the same
way, as Bootstrap's own dark hover is.

Colours are (r, g, b) tuples of 0-255 ints. Pure functions, no Django.
"""
import functools
import re

# Bootstrap's $body-bg-dark ($gray-900), the dark body background.
DARK_BODY_BG = (0x21, 0x25, 0x29)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
# WCAG 2 AA for normal text.
AA = 4.5
# Bootstrap's $link-shade-percentage: the hover step from the link colour.
HOVER_STEP = .2
# .mw-panel in _base.scss: rgba(var(--bs-body-bg-rgb), .8) over the Site surround.
PANEL_OPACITY = .8

_HEX = re.compile(r'^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


def parse_hex(colour):
    """'#4082c3', '4082c3' or '#48a' -> (r, g, b). Anything else -> None."""
    match = _HEX.match((colour or '').strip())
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 3:
        digits = ''.join(c * 2 for c in digits)
    return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))


def triple(rgb):
    """(64, 130, 195) -> '64, 130, 195', the form --bs-*-rgb variables take."""
    return ', '.join(str(c) for c in rgb)


def mix(rgb, other, weight):
    """`weight` (0-1) of `other` mixed into `rgb`, as Sass's tint and shade do."""
    return tuple(round(c + (o - c) * weight) for c, o in zip(rgb, other))


def luminance(rgb):
    """WCAG 2 relative luminance."""
    def channel(c):
        c /= 255
        return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return .2126 * r + .7152 * g + .0722 * b


def contrast(a, b):
    """WCAG 2 contrast ratio between two colours, 1 to 21."""
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


def _towards(backgrounds, ratio):
    """The end to move a colour towards: white, unless even white cannot
    reach `ratio` against every one of `backgrounds`."""
    return WHITE if all(contrast(WHITE, bg) >= ratio for bg in backgrounds) else BLACK


def _passes(rgb, backgrounds, ratio):
    return all(contrast(rgb, bg) >= ratio for bg in backgrounds)


def readable(rgb, *backgrounds, ratio=AA):
    """`rgb` unchanged if it already reaches `ratio` against every background
    (default: the dark body), otherwise the smallest whole-percent mix towards
    white (or black) that does."""
    backgrounds = backgrounds or (DARK_BODY_BG,)
    if _passes(rgb, backgrounds, ratio):
        return rgb
    end = _towards(backgrounds, ratio)
    for percent in range(1, 101):
        adjusted = mix(rgb, end, percent / 100)
        if _passes(adjusted, backgrounds, ratio):
            return adjusted
    return end


def hover(rgb, *backgrounds, ratio=AA):
    """The hover shade of a readable link colour: one further step the same
    way `readable` moves, so it stays at least as readable."""
    return mix(rgb, _towards(backgrounds or (DARK_BODY_BG,), ratio), HOVER_STEP)


def dark_panel(surround):
    """The dark metabar colour: the dark body at PANEL_OPACITY over the surround."""
    return mix(surround, DARK_BODY_BG, PANEL_OPACITY)


# Every page render asks, and a process serves few Sites: cache per colour pair.
@functools.lru_cache(maxsize=1024)
def dark_link_colours(colour, surround=None):
    """(link, hover) for the dark Color mode from a Site's hex link colour and
    hex background (surround) colour, or None if the link colour is not a hex
    colour. Without a usable surround only the dark body is considered."""
    rgb = parse_hex(colour)
    if rgb is None:
        return None
    backgrounds = [DARK_BODY_BG]
    surround_rgb = parse_hex(surround)
    if surround_rgb is not None:
        backgrounds.append(dark_panel(surround_rgb))
    link = readable(rgb, *backgrounds)
    return link, hover(link, *backgrounds)
