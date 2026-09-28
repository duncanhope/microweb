"""{% icon "name" %}: inline a vendored Bootstrap Icons SVG.

    {% load icon %}
    {% icon "search" %}                              decorative, hidden from screen readers
    {% icon "lock" label="Closed conversation" %}    role="img" with an aria-label
    {% icon "pencil" class="text-muted" %}           extra classes after "bi bi-pencil"

Icons are 1em square and filled with currentColor, so they follow the
surrounding text's size and colour in every Color mode. Give a label whenever
the icon is the only content of a link or button.

The SVGs live in core/icons/bootstrap-icons/ (see VERSION there). Each file is
read once per process. To add an icon, copy its SVG from the same release.
"""
import functools
import re
from pathlib import Path

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

ICON_DIR = Path(__file__).resolve().parent.parent / 'icons' / 'bootstrap-icons'

_NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
_SVG_RE = re.compile(r'^\s*<svg\b[^>]*\bclass="([^"]*)"[^>]*\bviewBox="([^"]*)"[^>]*>(.*)</svg>\s*$', re.S)


@functools.cache
def _load(name):
    """(class, viewBox, inner markup) of one icon, or TemplateSyntaxError."""
    path = ICON_DIR / ('%s.svg' % name)
    if not _NAME_RE.match(name) or not path.is_file():
        raise template.TemplateSyntaxError(
            'Unknown icon %r: there is no core/icons/bootstrap-icons/%s.svg. Copy it from '
            'Bootstrap Icons (see core/icons/bootstrap-icons/VERSION).' % (name, name))
    match = _SVG_RE.match(path.read_text(encoding='utf-8'))
    if not match:
        raise template.TemplateSyntaxError('Icon %r is not a Bootstrap Icons SVG: %s' % (name, path))
    css_class, view_box, inner = match.groups()
    inner = ''.join(line.strip() for line in inner.splitlines())
    return css_class, view_box, inner


@register.simple_tag
def icon(name, label=None, **kwargs):
    css_class = kwargs.pop('class', None)
    if kwargs:
        raise template.TemplateSyntaxError(
            '{%% icon %%} takes only label= and class=, not %s' % ', '.join(sorted(kwargs)))

    base_class, view_box, inner = _load(name)
    classes = '%s %s' % (base_class, css_class) if css_class else base_class
    # escape(), not format_html(): template string literals arrive marked safe,
    # and a quote in a literal label must still not break the attribute.
    if label:
        a11y = 'role="img" aria-label="%s"' % escape(label)
    else:
        a11y = 'aria-hidden="true" focusable="false"'
    return mark_safe(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" '
        'class="%s" viewBox="%s" %s>%s</svg>' % (escape(classes), view_box, a11y, inner))
