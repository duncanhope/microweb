from core.api import fetch
import logging

from django.http import HttpResponseBadRequest
from django.conf import settings

from core.framework import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_safe

from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Search
from core.api.resources import Site

from core.api.exceptions import APIException

from core.views import respond_with_error
from core.views import build_pagination_links

logger = logging.getLogger('search.views')
single_template = 'search.html'


def _parse_offset(request):
    """Return the requested offset, rounded down to a multiple of 25 (0 if missing or invalid)."""
    raw = request.GET.get('offset', '')
    if not (raw.isascii() and raw.isdigit()):
        return 0
    return max(0, int(raw) // settings.PAGE_SIZE * settings.PAGE_SIZE)

@require_safe
def single(request):
    searchParams = dict(request.GET.lists())
    searchParams['offset'] = _parse_offset(request)
    if searchParams.get('defaults'):
        searchParams['inTitle'] = 'true'
        searchParams['sort'] = 'date'

    url, params, headers = Search.build_request(request.get_host(), params=searchParams,
        access_token=request.access_token)
    request.view_requests.append(fetch.get(url, params=params, headers=headers))

    try:
        responses = response_list_to_dict(fetch.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    search = Search.from_api_response(responses[url])

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'content': search,
    }

    if responses[url].get('results'):
        view_data['pagination'] = build_pagination_links(responses[url]['results']['links'], search.results)

    return render(request, single_template, view_data)
