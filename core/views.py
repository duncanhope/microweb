from core.api import fetch
import datetime
import logging
import requests
import string
import random

from requests import RequestException

from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import parse_qs
from urllib.parse import urlunparse

from functools import wraps

from django.conf import settings

from django.core.exceptions import ValidationError
from django.http import HttpResponseNotFound
from django.http import HttpResponseForbidden
from django.http import HttpResponseServerError
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import redirect
from core.framework import get_template
from core.framework import render


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_safe

from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateView

from core.api.exceptions import APIException
from core.api.resources import api_url_to_gui_url
from core.api.resources import APIResource
from core.api.resources import Attachment
from core.api.resources import Comment
from core.api.resources import FileMetadata
from core.api.resources import Legal
from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Site
from core.api.resources import WhoAmI
from core.api.resources import is_ip_address

from core.api.resources import build_url

logger = logging.getLogger('core.views')


@require_safe
def health_ready(request):
    """Return a successful response when the Django web process is ready."""

    return HttpResponse('ok\n')


def build_error_view_data(request, include_user=False):
    """
    Best-effort context for error pages. Unknown hosts should not trigger a second failure.
    """

    view_data = {}
    view_requests = []
    whoami_url = None
    site_url = None

    try:
        if include_user and 'access_token' in request.COOKIES:
            request.access_token = request.COOKIES['access_token']
            whoami_url, params, headers = WhoAmI.build_request(request.get_host(), request.access_token)
            view_requests.append(fetch.get(whoami_url, params=params, headers=headers))

        site_url, params, headers = Site.build_request(request.get_host())
        view_requests.append(fetch.get(site_url, params=params, headers=headers))
    except (APIException, RequestException) as exc:
        if is_ip_address(request.get_host()):
            logger.info('Skipping error view context for IP host header %s' % request.get_host())
        else:
            logger.warning('Unable to build error view context for host %s: %s' % (request.get_host(), str(exc)))
        return view_data

    # Each answer on its own, so an expired token's 401 still leaves the Site.
    responses = {}
    for response in fetch.map(view_requests):
        try:
            responses.update(response_list_to_dict([response]))
        except APIException as exc:
            logger.warning('Unable to build error view context for host %s: %s' % (request.get_host(), str(exc)))

    if whoami_url and whoami_url in responses:
        view_data['user'] = Profile(responses[whoami_url], summary=False)

    if site_url and site_url in responses:
        view_data['site'] = Site(responses[site_url])

    return view_data

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """
    generates identifies that are used as cache busters in querystrings
    """
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))

def exception_handler(view_func):
    """
    Decorator for view functions that raises appropriate
    errors to the user and passes data to the error view.

    Forbidden and Not Found are the only statuses that are
    communicated to the visitor. All other errors should
    be handled in client code or a generic error page will
    be displayed.
    """

    @wraps(view_func)
    def decorator(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except APIException as e:
            if e.status_code == 401 or e.status_code == 403:
                return ErrorView.forbidden(request)
            elif e.status_code == 404:
                return ErrorView.not_found(request)
            elif e.status_code == 400:
                # Error code 14 indicates that the requested forum does not exist.
                if e.detail['errorCode'] == 14:
                    return HttpResponseRedirect('http://microcosm.app')
            else:
                raise
    return decorator

def respond_with_error(request, exception):

    if not isinstance(exception, APIException):
        logger.error(str(exception))
        return ErrorView.server_error(request)

    if exception.status_code == 404:
        return ErrorView.not_found(request)
    elif exception.status_code == 403:
        return ErrorView.forbidden(request)
    elif exception.status_code == 401:
        return ErrorView.requires_login(request)
    else:
        return ErrorView.server_error(request, exception)

def respond_with_refusal(request, response):
    """
    An API answer read straight from requests that refused the call, shown
    as the error page its status calls for rather than an empty 400.
    """

    try:
        APIResource.process_response(response.url, response)
    except APIException as exc:
        return respond_with_error(request, exc)
    return respond_with_error(request, APIException('Refused: %s' % response.url, response.status_code))

def require_authentication(view_func):
    """
    Returns HTTP 401 if request.access_token is not present.
    """

    @wraps(view_func)
    def decorator(request, *args, **kwargs):
        if hasattr(request, 'access_token'):
            return view_func(request, *args, **kwargs)
        else:
            return ErrorView.forbidden(request)
    return decorator

def build_pagination_links(request, paged_list):
    """
    This takes the data sent in the 'links' part of an api response
    and generates a dictionary of navigation links based on that.
    """

    if not hasattr(paged_list, 'page'):
        return {}

    page_nav = {
    'page': int(paged_list.page),
    'total_pages': int(paged_list.total_pages),
    'limit': int(paged_list.limit),
    'offset': int(paged_list.offset)
    }

    for item in request:
        item['href'] = api_url_to_gui_url(item['href'])
        page_nav[item['rel']] = item

    return page_nav

def process_attachments(request, comment):
    """
    For the provided request, check if files are to be attached or deleted
    from the provided comment. Raises a ValidationError if any files are larger
    than 30MB.
    """

    # Check if any existing comment attachments are to be deleted.
    if request.POST.get('attachments-delete'):
        attachments_delete = request.POST.get('attachments-delete').split(",")
        for fileHash in attachments_delete:
            Attachment.delete(
                request.get_host(),
                Comment.api_path_fragment,
                comment.id,
                fileHash,
                access_token=request.access_token,
            )

    # Check if any files have been uploaded with the request.
    if 'attachments' in request.FILES:
        for f in request.FILES.getlist('attachments'):
            file_request = FileMetadata.from_create_form(f)
            # Maximum file size is 30 MB.
            if len(file_request.file[f.name]) >= 31457280:
                raise ValidationError
            # Associate attachment with comment using attachments API.
            else:
                file_metadata = file_request.create(request.get_host(), request.access_token)
                Attachment.create(request.get_host(), file_metadata.file_hash,
                                  comment_id=comment.id, access_token=request.access_token, file_name=f.name)


def build_newest_comment_link(response, request=None):

    source = ''
    medium = ''
    campaign = ''

    if request is not None:
        source = request.GET.get('utm_source', '')
        medium = request.GET.get('utm_medium', '')
        campaign = request.GET.get('utm_campaign', '')

    response = response['comments']['links']
    for link in response:
        if link['rel'] == 'self':
            response = link['href']
    response = api_url_to_gui_url(response)
    pr = urlparse(response)
    queries = parse_qs(pr[4])
    frag = ""

    if queries.get('comment_id'):
        frag = 'comment' + queries['comment_id'][0]
        del queries['comment_id']

    # queries is a dictionary of 1-item lists (as we don't re-use keys in our query string)
    # urlencode will encode the lists into the url (offset=[25]) etc.  So get the values straight.
    for (key, value) in queries.items():
        queries[key] = value[0]

    # preserve utm tracking from original request
    if source and medium and campaign:
        queries['utm_source'] = source
        queries['utm_medium'] = medium
        queries['utm_campaign'] = campaign

    queries = urlencode(queries)
    response = urlunparse((pr[0], pr[1], pr[2], pr[3], queries, frag))
    return response


class LegalView(object):
    list_template = 'legals.html'
    single_template = 'legal.html'

    @staticmethod
    @require_safe
    def list(request):
        try:
            responses = response_list_to_dict(fetch.map(request.view_requests))
        except APIException as exc:
            return respond_with_error(request, exc)

        view_data = {
            'site': Site(responses[request.site_url]),
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site_section': 'legal'
        }
        return render(request, LegalView.list_template, view_data)

    @staticmethod
    @require_safe
    def single(request, doc_name):
        if not doc_name in ['cookies', 'privacy', 'terms']:
            return ErrorView.not_found(request)

        url, params, headers = Legal.build_request(request.get_host(), doc=doc_name)
        request.view_requests.append(fetch.get(url, params=params, headers=headers))
        try:
            responses = response_list_to_dict(fetch.map(request.view_requests))
        except APIException as exc:
            return respond_with_error(request, exc)

        legal = Legal.from_api_response(responses[url])

        view_data = {
            'site': Site(responses[request.site_url]),
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'content': legal,
            'site_section': 'legal',
            'page_section': doc_name
        }
        return render(request, LegalView.single_template, view_data)


class ErrorView(object):
    @staticmethod
    def not_found(request, exception=None):
        view_data = build_error_view_data(request, include_user=True)
        return HttpResponseNotFound(get_template(request, '404.html').render(view_data, request))

    @staticmethod
    def forbidden(request, exception=None):
        view_data = build_error_view_data(request, include_user=True)
        return HttpResponseForbidden(get_template(request, '403.html').render(view_data, request))

    @staticmethod
    def server_error(request, exception=None):
        view_data = build_error_view_data(request)

        # Provide detailed error if returned in the response.
        if hasattr(exception, 'detail') and isinstance(exception.detail, dict):
            if 'errorDetail' in exception.detail:
                view_data['detail'] = exception.detail['errorDetail']

        return HttpResponseServerError(get_template(request, '500.html').render(view_data, request))

    @staticmethod
    def requires_login(request):
        view_data = build_error_view_data(request)
        view_data['logout'] = True

        return HttpResponseForbidden(get_template(request, '403.html').render(view_data, request))

class AuthenticationView(object):

    @staticmethod
    @csrf_exempt
    @require_http_methods(["POST"])
    def login(request):
        """
        Log a user in using Persona.

        Creates an access_token using a persona assertion and the client secret.

        Sets this access token as a cookie.

        'target_url' based as a GET parameter determines where the user is
        redirected.
        """

        target_url = request.POST.get('target_url')
        assertion = request.POST.get('Assertion')
        postdata = {
            'Assertion': assertion,
            'ClientSecret':settings.CLIENT_SECRET
        }

        url = build_url(request.get_host(), ['auth'])
        try:
            response = requests.post(url, data=postdata, headers={})
        except RequestException:
            return ErrorView.server_error(request)

        access_token = response.json()['data']
        if access_token is None or access_token == '':
            return ErrorView.server_error(request)

        if target_url is None or target_url == '':
            target_url = '/'

        response = HttpResponseRedirect(target_url)
        expires = datetime.datetime.fromtimestamp(2 ** 31 - 1)
        response.set_cookie('access_token', access_token, expires=expires, httponly=True)
        return response

    @staticmethod
    @require_http_methods(["POST"])
    def logout(request):
        """
        Log a user out.

        Issues a DELETE request to the backend for the user's access_token, and
        issues a delete cookie header in response to clear the user's
        access_token cookie.
        """

        response = redirect('/')
        if 'access_token' in request.COOKIES:
            response.set_cookie('access_token', '', expires="Thu, 01 Jan 1970 00:00:00 GMT")
            url = build_url(request.get_host(), ['auth', request.access_token])
            try:
                requests.post(url, params={'method': 'DELETE', 'access_token': request.access_token})
            except RequestException:
                return ErrorView.server_error(request)

        return response

class Auth0View(object):

    @staticmethod
    @csrf_exempt
    def login(request):
        """
        Log a user in using auth0

        Creates an access_token using an auth0 code and state.

        Sets this access token as a cookie.

        'target_url' based as a GET parameter determines where the user is
        redirected.
        """

        code = request.GET.get('code')
        state = request.GET.get('state')
        target_url = request.GET.get('target_url')

        postdata = {
            'Code': code,
            'State': state,
            'ClientSecret': settings.CLIENT_SECRET
        }

        url = build_url(request.get_host(), ['auth0'])
        try:
            response = requests.post(url, data=postdata, headers={})
        except RequestException:
            return ErrorView.server_error(request)

        access_token = response.json()['data']
        if access_token is None or access_token == '':
            return ErrorView.server_error(request)

        if target_url is None or target_url == '':
            target_url = state

        if target_url is None or target_url == '':
            target_url = '/'

        # Add cachebuster as the unauth'd page may be very aggressively cached
        pr = urlparse(target_url)
        qs = parse_qs(pr[4])
        qs.update({'cachebuster': id_generator()})
        target_url = urlunparse((pr[0], pr[1], pr[2], pr[3], urlencode(qs), pr[5]))

        # Redirect and set cookie
        resp = HttpResponseRedirect(target_url)
        expires = datetime.datetime.fromtimestamp(2 ** 31 - 1)
        resp.set_cookie('access_token', access_token, expires=expires, httponly=True)

        return resp

def echo_headers(request):
    view_data = '<html><body><table>'
    for key in request.META.keys():
        view_data += '<tr><td>%s</td><td>%s</td></tr>' % (key, request.META[key])
    view_data += '</table></body></html>'
    return HttpResponse(view_data, content_type='text/html')


class FaviconView(RedirectView):
    def get_redirect_url(self, **kwargs):
        return settings.STATIC_URL + 'img/favico.png'


class RobotsView(TemplateView):
    template_name = 'robots.txt'
    content_type = 'text/plain'

    def get_context_data(self, **kwargs):
        return super(RobotsView, self).get_context_data(**kwargs)
