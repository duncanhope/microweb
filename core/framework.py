"""Bootstrap 3 and 5 side by side during the migration (docs/bootstrap5-plan.md).

A page renders on Bootstrap 5 only when the visitor asks for it (``?bs=5``,
remembered in the ``bs`` cookie) and the page's own template exists in
``settings.BS5_TEMPLATE_DIR``. Every other page, and every visitor without
the cookie, gets Bootstrap 3 exactly as before. Inside a Bootstrap 5 page,
includes and inclusion tags resolve in the Bootstrap 5 tree first and fall
back to the Bootstrap 3 template of the same name.

Views call ``render`` from here instead of ``django.shortcuts.render``; error
views use ``get_template``. BS5-16 makes Bootstrap 5 the default and BS5-18
deletes this module.
"""
import os

from django.conf import settings
from django.shortcuts import render as django_render
from django.template import loader

COOKIE = 'bs'
BS5_ENGINE = 'bs5'
COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def wants_bs5(request):
    return (request.GET.get(COOKIE) or request.COOKIES.get(COOKIE)) == '5'


def has_bs5_template(template_name):
    return os.path.isfile(os.path.join(settings.BS5_TEMPLATE_DIR, template_name))


def engine_for(request, template_name):
    """The template engine name to render ``template_name`` with for this request."""
    if wants_bs5(request) and has_bs5_template(template_name):
        return BS5_ENGINE
    return None


def render(request, template_name, context=None, content_type=None, status=None, using=None):
    """``django.shortcuts.render`` that picks the Bootstrap 5 engine when it should,
    and remembers an explicit ``?bs=3`` or ``?bs=5`` in the ``bs`` cookie."""
    if using is None:
        using = engine_for(request, template_name)
    response = django_render(request, template_name, context, content_type, status, using)
    choice = request.GET.get(COOKIE)
    if choice in ('3', '5'):
        response.set_cookie(COOKIE, choice, max_age=COOKIE_MAX_AGE, samesite='Lax',
                            secure=request.is_secure(), httponly=True)
    return response


def get_template(request, template_name):
    """``loader.get_template`` for views that build their own response, such as error pages."""
    return loader.get_template(template_name, using=engine_for(request, template_name))
