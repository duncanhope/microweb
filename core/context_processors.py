"""Template context for the Bootstrap 5 engine (settings.TEMPLATES, NAME 'bs5')."""
from core.middleware.context import color_mode as cookie_color_mode

# (value, name, icon) of each Color mode in core.middleware.context.COLOR_MODES,
# in the toggle's order.
COLOR_MODE_CHOICES = (
    ('light', 'Light', 'sun-fill'),
    ('dark', 'Dark', 'moon-stars-fill'),
    ('auto', 'Auto', 'circle-half'),
)


def color_mode(request):
    """The viewer's Color mode (`color_mode`) and the toggle's choices
    (`color_modes`). ContextMiddleware reads the cookie; a request that
    skipped it, such as an error page, reads it here."""
    mode = getattr(request, 'color_mode', None) or cookie_color_mode(request)
    return {
        'color_mode': mode,
        'color_modes': [
            {'value': value, 'name': name, 'icon': icon, 'chosen': value == mode}
            for value, name, icon in COLOR_MODE_CHOICES
        ],
    }
