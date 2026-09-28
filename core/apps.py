from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Only the visual harness (microweb/visual_settings.py) records or
        # replays API calls; production and unit tests never wrap requests.
        if getattr(settings, 'VISUAL_HARNESS', False):
            from core.harness import recorder
            recorder.install(
                settings.HARNESS_FIXTURES_DIR,
                settings.HARNESS_MODE,
                settings.HARNESS_SESSION,
            )
