import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Do not change these settings. Override them in local_settings.py if necessary.
DEBUG = False

# ALLOWED_HOSTS would normally pin the hosts Django serves. Since we allow
# customers to CNAME their domain to a microcosm site, we cannot make use of
# this feature. Host is verified in the API.
ALLOWED_HOSTS = [
    '*',
]

# There is no database. All content lives behind the Microcosm API.
DATABASES = {}

TIME_ZONE = 'Europe/London'
LANGUAGE_CODE = 'en-gb'

# Internationalisation settings.
USE_I18N = True
USE_TZ = True

## DO NOT ENABLE THIS, it will break editing and other places that embed identifiers
## within forms.
#USE_THOUSAND_SEPARATOR = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# In production these are served by whitenoise.
STATIC_ROOT = '/srv/www/django/microweb/static/'

# URL prefix for static files.
STATIC_URL = '/static/'
STATICFILES_DIRS = ()
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.static',
            ],
        },
    },
    # Bootstrap 5 migration (docs/bootstrap5-plan.md). core/framework.py picks
    # this engine for a page whose template exists in BS5_TEMPLATE_DIR; its
    # includes resolve there first and fall back to the Bootstrap 3 templates.
    # Removed in BS5-18, when core/templates_bs5/ becomes core/templates/.
    {
        'NAME': 'bs5',
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(os.path.dirname(PROJECT_ROOT), 'core', 'templates_bs5')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'core.context_processors.color_mode',
            ],
        },
    },
]

BS5_TEMPLATE_DIR = TEMPLATES[1]['DIRS'][0]

MIDDLEWARE = [
    # Static file serving
    'whitenoise.middleware.WhiteNoiseMiddleware',

    # Note: if using messages, enable the sessions middleware too
    'django.middleware.common.CommonMiddleware',

    # CSRF protection on form submission
    'django.middleware.csrf.CsrfViewMiddleware',

    # preconnect for 3rd party assets
    'core.middleware.preconnect.PreconnectMiddleware',

    # CORS for text/html pages
    'core.middleware.cors.CorsMiddleware',

    # Convenience for request context like site, user account, etc.
    # Sits below Preconnect/Cors so that responses it short-circuits
    # (e.g. 404 for unresolved hosts) still pass through them.
    'core.middleware.context.ContextMiddleware',

    # Redirect to custom domain, if one exists for the site
    'core.middleware.redirect.DomainRedirectMiddleware',
]

ROOT_URLCONF = 'microweb.urls'

# Leaves the Playwright checks (tag 'browser') out unless --tag browser.
TEST_RUNNER = 'core.test_runner.MicrowebTestRunner'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'microweb.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'conversations',
    'events',
    'microcosms',
    'huddles',
    'comments',
    'profiles',
    'updates',
    'search',
    'trending',
    'moderation',
    'ignored',
    'today',
    'redirect',
)

# The values below in must be initialised in local_settings.py
# Example values can be found in local_settings.py.example

# Credentials generated when registering an application.
from microweb.local_settings import CLIENT_ID
from microweb.local_settings import CLIENT_SECRET

# Microcosm API settings.
from microweb.local_settings import API_SCHEME
from microweb.local_settings import API_DOMAIN_NAME
from microweb.local_settings import API_PATH
from microweb.local_settings import API_VERSION

if API_SCHEME == '' or API_DOMAIN_NAME == '' or API_PATH == '' or API_VERSION == '':
    raise Exception('Please define API settings in local_settings.py')

# Mostly used for site information cache. Compulsory.
from microweb.local_settings import MEMCACHE_HOST
from microweb.local_settings import MEMCACHE_PORT

# Page size for list views: Microcosms, Huddles, etc.
from microweb.local_settings import PAGE_SIZE

# In production, all logging goes to stdout which is redirected by gunicorn.
# This isn't ideal (we can't route to mulitple places), but works well enough.
from microweb.local_settings import LOGGING

# Make this unique, and don't share it with anybody.
from microweb.local_settings import SECRET_KEY

# Allows shadowing of DEBUG for development.
from microweb.local_settings import DEBUG

# Allow override of STATIC_ROOT for production
from microweb.local_settings import STATIC_ROOT

# Site information cache (CNAME lookups, Site objects).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '%s:%s' % (MEMCACHE_HOST, MEMCACHE_PORT),
        'OPTIONS': {
            'use_pooling': True,
            # Treat memcached outages as cache misses rather than errors.
            'ignore_exc': True,
            'no_delay': True,
        },
    },
}
