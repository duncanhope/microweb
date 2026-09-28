"""Harness server: one Django tree, frozen in time, API recorded or replayed.

Run by `manage.py shoot` as a subprocess, never by hand:

    python core/harness/serve.py --root TREE --port N --freeze ISO
        [--settings microweb.visual_settings]

With `--settings microweb.visual_settings` (this checkout), CoreConfig
installs the recorder from HARNESS_* environment variables. Any other
settings module means a tree from another git ref, which may predate the
harness: this script then loads this checkout's recorder by file path and
swaps memcached for an in-process cache itself. Either way both sides of a
comparison share one recorder and one fixture format.

Time is frozen in this process only (freezegun), so `|timesince` renders
against the recording's timestamp while the shoot process keeps real time.
"""
import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_recorder():
    spec = importlib.util.spec_from_file_location('microweb_harness_recorder', os.path.join(HERE, 'recorder.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--freeze', required=True)
    parser.add_argument('--settings', default='microweb.settings')
    args = parser.parse_args()

    import freezegun
    freezegun.freeze_time(args.freeze, tick=False).start()

    root = os.path.abspath(args.root)
    sys.path[0] = root
    os.chdir(root)
    os.environ['DJANGO_SETTINGS_MODULE'] = args.settings

    from django.conf import settings
    if not getattr(settings, 'VISUAL_HARNESS', False):
        settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
        load_recorder().install(
            os.environ['HARNESS_FIXTURES'],
            os.environ.get('HARNESS_MODE', 'replay'),
            os.environ.get('HARNESS_SESSION', ''),
        )

    import django
    django.setup()

    from django.contrib.staticfiles.handlers import StaticFilesHandler
    from django.core.servers.basehttp import run
    from django.core.wsgi import get_wsgi_application

    # StaticFilesHandler serves core/static through the finders whatever
    # DEBUG says, like `runserver --insecure`.
    run('127.0.0.1', args.port, StaticFilesHandler(get_wsgi_application()), threading=True)


if __name__ == '__main__':
    main()
