import logging
from core.api import fetch

from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect

from core.api.exceptions import APIException
from core.api.resources import is_ip_address
from core.api.resources import Site
from core.api.resources import WhoAmI
from core.framework import get_template

logger = logging.getLogger('core.middleware.context')

# The viewer's Color mode (BS5-06), chosen with the navbar toggle and kept in
# a per-host cookie. Auto follows the system's prefers-color-scheme.
COLOR_MODE_COOKIE = 'color_mode'
COLOR_MODES = ('light', 'dark', 'auto')
DEFAULT_COLOR_MODE = 'auto'


def color_mode(request):
    """The Color mode the request's cookie asks for; anything else is auto."""
    mode = request.COOKIES.get(COLOR_MODE_COOKIE)
    return mode if mode in COLOR_MODES else DEFAULT_COLOR_MODE

class ContextMiddleware:
    """
    Provides request context such as the current site and authentication status.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.process_request(request)
        if response is not None:
            return response
        return self.get_response(request)

    def process_request(self, request):
        """
        Checks for access_token cookie and appends it to the request object if present.
        Sets request.color_mode from the color_mode cookie for the templates.

        All request objects have a view_requests attribute which is a list of requests
        that will be executed by core.api.fetch to fetch data for the view.
        """

        # The readiness endpoint must only verify that Django is serving requests;
        # it must not depend on the external Microcosm API being available.
        if request.path == '/health/ready':
            return None

        request.color_mode = color_mode(request)
        request.access_token = None
        request.whoami_url = ''
        request.view_requests = []

        try:
            if 'access_token' in request.COOKIES:
                # Clean up empty access token.
                if request.COOKIES['access_token'] == '':
                    response = HttpResponseRedirect('/')
                    response.set_cookie('access_token', '', expires="Thu, 01 Jan 1970 00:00:00 GMT")
                    return response
                request.access_token = request.COOKIES['access_token']
                request.whoami_url, params, headers = WhoAmI.build_request(request.get_host(), request.access_token)
                request.view_requests.append(fetch.get(request.whoami_url, params=params, headers=headers))

            request.site_url, params, headers = Site.build_request(request.get_host())
            request.view_requests.append(fetch.get(request.site_url, params=params, headers=headers))
        except APIException as e:
            if e.status_code in [400, 404]:
                if is_ip_address(request.get_host()):
                    logger.info('Rejecting IP host header %s' % request.get_host())
                    return HttpResponseNotFound()
                logger.warning('Rejecting unresolved host %s: %s' % (request.get_host(), str(e)))
                # A mistyped custom domain: the plain Not Found page, with no
                # Site to dress it, since the host has none.
                return HttpResponseNotFound(get_template(request, '404.html').render({}, request))
            raise
