"""Settings for the visual harness (manage.py shoot and the browser checks).

`shoot` starts its server with these. To poke at a recording by hand:
`python manage.py runserver --settings=microweb.visual_settings`.
Nothing here is used in production.
"""
import os

from microweb.settings import *  # noqa: F401,F403
from microweb.settings import PROJECT_ROOT

VISUAL_HARNESS = True

# Recordings hold member content and private huddles, so they live in the
# git-ignored .harness/ folder and never in a commit.
HARNESS_FIXTURES_DIR = os.environ.get(
    'HARNESS_FIXTURES',
    os.path.join(os.path.dirname(PROJECT_ROOT), '.harness', 'fixtures'),
)
# 'record' fetches from the live API and writes fixtures. 'replay' serves
# fixtures only and never touches the network.
HARNESS_MODE = os.environ.get('HARNESS_MODE', 'replay')
# Names one recording run, so repeat calls within it reuse one answer.
HARNESS_SESSION = os.environ.get('HARNESS_SESSION', '')

# No memcached: each harness server starts with an empty in-process cache.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}
