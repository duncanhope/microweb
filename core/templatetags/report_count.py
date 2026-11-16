from django import template

from core.api.exceptions import APIException
from core.api.resources import ReportList


register = template.Library()


@register.simple_tag
def report_count(user, request):
    permissions = getattr(getattr(user, 'meta', None), 'permissions', None)
    # A PermissionSet from the API, or a plain dict as the templates also accept.
    allowed = (permissions.get if isinstance(permissions, dict)
               else lambda name: getattr(permissions, name, False))
    if not permissions or not (allowed('siteOwner') or allowed('moderator')):
        return 0
    # A template rendered outside a request (render_to_string) has no host
    # or token to ask with.
    if not hasattr(request, 'get_host'):
        return 0

    try:
        return ReportList.open_count(request.get_host(), getattr(request, 'access_token', None))
    except APIException:
        return 0
