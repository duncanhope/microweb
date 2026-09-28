import random
import string
import json
import os

import unittest
from django.conf import settings
from django.test.client import RequestFactory

from unittest.mock import patch

from core.views import build_pagination_links
from core.views import build_newest_comment_link

from core.api.resources import Conversation
from core.api.resources import Microcosm
from core.api.resources import Profile
from core.api.resources import Site
from core.api.resources import Event
from core.api.resources import NEGATIVE_CNAME_CACHE_TTL
from core.api.resources import NEGATIVE_CNAME_CACHE_VALUE
from core.api.resources import build_url
from core.api.resources import is_ip_address
from core.api.exceptions import APIException
from core.middleware.context import ContextMiddleware
from core.views import ErrorView

TEST_ROOT = os.path.dirname(os.path.abspath(__file__))


def generate_location():
    # Construct a random subdomain string
    subdomain = ''
    for x in range(10):
        subdomain += random.choice(string.ascii_lowercase)
    return '%s.microcosm.app' % subdomain


class BuildURLTests(unittest.TestCase):
    """
    Verify that helpers.build_url() builds valid URLs.
    """

    subdomain_key = 'abc.'

    def testWithTrailingSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['resource/', '1/', 'extra/'])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/resource/1/extra'

    def testWithPrependedSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['/resource', '/1', '/extra'])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/resource/1/extra'

    def testWithDuplicateSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['resource/', '/1/', '/extra/'])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/resource/1/extra'

    def testWithNoSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['resource', '1', 'extra'])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/resource/1/extra'

    def testEmptyFragments(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), [])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION

    def testIntFragment(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), [1, 2, 3])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/1/2/3'

    def testInvalidFragment(self):
        with self.assertRaises(AssertionError):
            build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['resource', '1', 'ex/tra'])

    def testFailCustomDomains(self):
        with self.assertRaises(APIException):
            build_url((BuildURLTests.subdomain_key + 'example.org'), ['resource', '1', 'ex/tra'])

    @patch('core.api.resources.mc')
    @patch('requests.get')
    def testRejectsIpHostsWithoutLookup(self, mock_get, mock_mc):
        mock_mc.get.return_value = None
        with self.assertRaises(APIException) as context:
            build_url('139.162.251.45', ['resource'])

        assert context.exception.status_code == 404
        assert 'Refusing to resolve IP host 139.162.251.45' == context.exception.message
        assert not mock_get.called

    def testIsIpAddress(self):
        assert is_ip_address('139.162.251.45')
        assert is_ip_address('139.162.251.45:443')
        assert not is_ip_address('islingtoncc.microcosm.app')

    @patch('core.api.resources.mc')
    @patch('core.api.resources.Site.resolve_cname')
    def testCachedNegativeHostSkipsLookup(self, mock_resolve_cname, mock_mc):
        mock_mc.get.return_value = NEGATIVE_CNAME_CACHE_VALUE

        with self.assertRaises(APIException) as context:
            build_url('missing.example.org', ['resource'])

        assert context.exception.status_code == 404
        assert 'Cached unresolved host missing.example.org' == context.exception.message
        assert not mock_resolve_cname.called

    @patch('core.api.resources.mc')
    @patch('core.api.resources.Site.resolve_cname')
    def testUnknownHostIsNegativeCached(self, mock_resolve_cname, mock_mc):
        mock_mc.get.return_value = None
        mock_resolve_cname.side_effect = APIException('Error resolving CNAME missing.example.org', 404)

        with self.assertRaises(APIException) as context:
            build_url('missing.example.org', ['resource'])

        assert context.exception.status_code == 404
        mock_mc.set.assert_called_once_with('missing.example.org_cname', NEGATIVE_CNAME_CACHE_VALUE, timeout=NEGATIVE_CNAME_CACHE_TTL)


class PaginationTests(unittest.TestCase):
    """
    Verify that pagination nav links are built correctly for all pages
    where pagination can occur.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def testLinks(self):
        """
        Assert that a response containing a 'next page' link is correctly represnted in navigation.
        """

        host = generate_location()
        path = '/conversations/1'
        # Create a request for a list of microcosms
        request = self.factory.get(path, HTTP_HOST=host)
        request.access_token = None
        request.whoami = None
        request.site = None

        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation_with_paginated_comments.json')).read())['data']
        conversation = Conversation.from_api_response(data)
        with patch('requests.get') as mock:
            mock.return_value.json.return_value = conversation
            pagination_nav = build_pagination_links(request, conversation.comments)

        assert pagination_nav['page'] == 1
        assert pagination_nav['offset'] == 0
        assert pagination_nav['total_pages'] == 2
        assert pagination_nav['limit'] == 25

    def testBuildNewestLink(self):
        """
        Assert that build_newest_comment_link parses comment links and builds
        the new location correctly.
        """

        links = [{
                    "rel": "self",
                    "href": "/api/v1/conversations/161991?comment_id=7050281",
                    "title": "1"
                    },
                {
                    "rel": "next",
                    "href": "/api/v1/conversations/161991?comment_id=7050281&offset=25",
                    "title": "2"
                    },
                {
                    "rel": "last",
                    "href": "/api/v1/conversations/161991?comment_id=7050281&offset=875",
                    "title": "36"
                }]
        response = {"comments": {"links": links}}

        location = build_newest_comment_link(response)
        assert location == '/conversations/161991/#comment7050281'


class ResourceTests(unittest.TestCase):

    """
    Basic initialisation and serialisation tests for API resources.
    TODO: in some cases, as_dict is a property, in others it is a callable.
    """

    def testMicrocosmInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data']
        Microcosm.from_api_response(data)

    def testMicrocosmAsDict(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data']
        microcosm = Microcosm.from_api_response(data)
        microcosm.as_dict

    def testMicrocosmSummaryInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data']
        Microcosm.from_summary(data)

    def testConversationInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation_with_comment.json')).read())['data']
        Conversation.from_api_response(data)

    def testCommentedConversationInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation_without_comment.json')).read())['data']
        Conversation.from_api_response(data)

    def testConversationAsDict(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation_without_comment.json')).read())['data']
        conversation = Conversation.from_api_response(data)
        conversation.as_dict()

    def testEventInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'event_without_comment.json')).read())['data']
        Event.from_api_response(data)

    def testCommentedEventInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'event_with_comment.json')).read())['data']
        Event.from_api_response(data)

    def testEventAsDict(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'event_without_comment.json')).read())['data']
        event = Event.from_api_response(data)
        event.as_dict()

    def testWhoamiInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'whoami.json')).read())['data']
        Profile(data)

    def testProfileInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data']
        Profile(data)

    def testProfileAsDict(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data']
        profile = Profile(data)
        profile.as_dict

    def testProfileSummaryInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data']
        Profile(data, summary=True)

    def testSiteInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'site.json')).read())['data']
        Site(data)


class ErrorHandlingTests(unittest.TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @patch('core.middleware.context.Site.build_request')
    def testContextMiddlewareReturns404ForUnknownHost(self, mock_build_request):
        request = self.factory.get('/', HTTP_HOST='139.162.251.45')
        mock_build_request.side_effect = APIException('Error resolving CNAME 139.162.251.45', 404)

        middleware = ContextMiddleware(lambda r: None)
        response = middleware.process_request(request)

        assert response.status_code == 404

    @patch('core.views.get_template')
    @patch('core.views.Site.build_request')
    def testServerErrorDoesNotRecurseOnUnknownHost(self, mock_build_request, mock_get_template):
        request = self.factory.get('/', HTTP_HOST='139.162.251.45')
        mock_build_request.side_effect = APIException('Error resolving CNAME 139.162.251.45', 404)

        class DummyTemplate(object):
            def render(self, context, request=None):
                return 'server error'

        mock_get_template.return_value = DummyTemplate()
        response = ErrorView.server_error(request)

        assert response.status_code == 500
        assert response.content == b'server error'
