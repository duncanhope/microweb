from django.test.runner import DiscoverRunner

BROWSER_TAG = 'browser'


class MicrowebTestRunner(DiscoverRunner):
    """Keeps the Playwright checks out of a plain `manage.py test`.

    Browser checks live in modules named `*browser_tests.py`, which the
    default `test*.py` discovery pattern never imports, so a plain run needs
    neither Playwright nor a browser. `manage.py test --tag browser` widens
    the pattern to find them, and the tag filter keeps only them.
    """

    def __init__(self, pattern=None, tags=None, exclude_tags=None, **kwargs):
        if tags and BROWSER_TAG in tags:
            if pattern in (None, 'test*.py'):
                pattern = '*test*.py'
        else:
            exclude_tags = set(exclude_tags or ()) | {BROWSER_TAG}
        super().__init__(pattern=pattern, tags=tags, exclude_tags=exclude_tags, **kwargs)
