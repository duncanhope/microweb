import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from core.sass_sources import OUTPUT, REPO_ROOT, recorded_hash, source_hash


class CompiledCSSFreshnessTests(SimpleTestCase):

    def test_bs5_css_was_built_from_the_current_sass_sources(self):
        recorded = recorded_hash(REPO_ROOT / OUTPUT)
        self.assertIsNotNone(recorded, '%s has no source hash header. Run bin/build-css.' % OUTPUT)
        self.assertEqual(
            recorded, source_hash(),
            '%s is stale: the Sass sources changed since it was built. '
            'Run bin/build-css and commit the result.' % OUTPUT)

    def test_source_hash_changes_when_a_scss_file_changes(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root, 'scss', '_tokens.scss')
            source.parent.mkdir()
            source.write_text('$primary: #4082c3;\n')
            Path(root, 'scss', 'notes.txt').write_text('not Sass')
            before = source_hash(root, ['scss'])

            Path(root, 'scss', 'notes.txt').write_text('still not Sass')
            self.assertEqual(before, source_hash(root, ['scss']))

            source.write_text('$primary: #000;\n')
            self.assertNotEqual(before, source_hash(root, ['scss']))
