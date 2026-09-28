"""Hash of the Sass sources behind the compiled Bootstrap 5 stylesheet.

bin/build-css writes this hash into the first line of bs5.min.css, and
core/tests/test_css_fresh.py recomputes it, so a Sass edit committed without
a rebuild fails the tests. Standard library only: bin/build-css imports this
module without Django.

The hash is the SHA-256 of a sha256sum-style manifest of every .scss file
under SOURCE_DIRS, sorted by repo-relative path. The same value from a shell:

    find core/static/themes/1/scss core/static/scss/vendor/bootstrap \\
        -type f -name '*.scss' | LC_ALL=C sort | xargs sha256sum | sha256sum
"""
import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIRS = (
    'core/static/themes/1/scss',
    'core/static/scss/vendor/bootstrap',
)
ENTRY_POINT = 'core/static/themes/1/scss/site.scss'
LOAD_PATH = 'core/static/scss/vendor'
OUTPUT = 'core/static/themes/1/css/bs5.min.css'

HEADER_PREFIX = '/* bs5.min.css: built by bin/build-css from Sass sources sha256:'
_HEADER_RE = re.compile(re.escape(HEADER_PREFIX) + r'([0-9a-f]{64})\b')


def source_hash(root=REPO_ROOT, source_dirs=SOURCE_DIRS):
    root = Path(root)
    files = sorted(
        path.relative_to(root).as_posix()
        for source_dir in source_dirs
        for path in (root / source_dir).rglob('*.scss')
    )
    manifest = ''.join(
        '%s  %s\n' % (hashlib.sha256((root / name).read_bytes()).hexdigest(), name)
        for name in files
    )
    return hashlib.sha256(manifest.encode('utf-8')).hexdigest()


def header(digest, sass_version):
    return '%s%s (dart-sass %s) */' % (HEADER_PREFIX, digest, sass_version)


def recorded_hash(css_path):
    """The source hash in the compiled CSS's first line, or None if absent."""
    with open(css_path, encoding='utf-8-sig') as css:
        match = _HEADER_RE.match(css.readline())
    return match.group(1) if match else None
