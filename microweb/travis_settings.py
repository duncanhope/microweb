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

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
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
    # Bootstrap 5 migration engine; mirrors microweb/settings.py.
    {
        'NAME': 'bs5',
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(os.path.dirname(PROJECT_ROOT), 'core', 'templates_bs5')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.static',
            ],
        },
    },
]

BS5_TEMPLATE_DIR = TEMPLATES[1]['DIRS'][0]

MIDDLEWARE = [
    # Note: if using messages, enable the sessions middleware too
    'django.middleware.common.CommonMiddleware',

    # CSRF protection on form submission
    'django.middleware.csrf.CsrfViewMiddleware',

    # preconnect for 3rd party assets
    'core.middleware.preconnect.PreconnectMiddleware',

    # CORS for text/html pages
    'core.middleware.cors.CorsMiddleware',

    # Convenience for request context like site, user account, etc.
    'core.middleware.context.ContextMiddleware',

    # Redirect to custom domain, if one exists for the site
    'core.middleware.redirect.DomainRedirectMiddleware',
]

ROOT_URLCONF = 'microweb.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'microweb.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'core',
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

CLIENT_ID = 1
CLIENT_SECRET = ''
API_SCHEME = 'https://'
API_DOMAIN_NAME = 'microcosm.app'
API_PATH = 'api'
API_VERSION = 'v1'
MEMCACHE_HOST = '127.0.0.1'
MEMCACHE_PORT = 11211
PAGE_SIZE = 25
SECRET_KEY = 'changeme'
DEBUG = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '%s:%s' % (MEMCACHE_HOST, MEMCACHE_PORT),
        'OPTIONS': {
            'use_pooling': True,
            'ignore_exc': True,
            'no_delay': True,
        },
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        },
    'handlers': {
        'stdout':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        },
    'loggers': {
        'django': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate': True,
            },
        'django.request': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate': True,
            },
        'microcosm.views': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate' : True,
            },
        'microcosm.middleware': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate' : True,
            }
    }
}
