"""Ensure deployed HTML references the current CSS and JavaScript assets."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import build_site


class TestDeployAssetVersions(unittest.TestCase):
    def test_assets_change_version_when_contents_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data.json').write_text(json.dumps({'conferences': [], 'awards': []}), encoding='utf-8')
            (root / 'index.html').write_text(
                '<link rel="stylesheet" href="styles.css" /><link rel="stylesheet" href="dark-theme.css" /><link rel="stylesheet" href="abstract-matcher.css" /><link rel="stylesheet" href="accessibility.css" />'
                '<script src="data.js"></script><script src="abstract-matcher.js"></script><script src="app.js"></script>', encoding='utf-8')
            for filename in ('app.js', 'data.js', 'styles.css', 'dark-theme.css', 'abstract-matcher.js', 'abstract-matcher.css', 'accessibility.css'):
                (root / filename).write_text('initial content', encoding='utf-8')
            with patch.object(build_site, 'ROOT', root), patch.object(build_site.subprocess, 'run'):
                build_site.build(root / 'dist')
                html = (root / 'dist' / 'index.html').read_text(encoding='utf-8')
                digest = hashlib.sha256(b'initial content').hexdigest()[:12]
                self.assertIn(f'src="app.js?v={digest}"', html)
                self.assertIn(f'src="data.js?v={digest}"', html)
                self.assertIn(f'href="styles.css?v={digest}"', html)
                self.assertIn(f'href="dark-theme.css?v={digest}"', html)
                self.assertIn(f'href="abstract-matcher.css?v={digest}"', html)
                self.assertIn(f'href="accessibility.css?v={digest}"', html)
                self.assertIn(f'src="abstract-matcher.js?v={digest}"', html)
                (root / 'app.js').write_text('new content', encoding='utf-8')
                build_site.build(root / 'dist')
                new_html = (root / 'dist' / 'index.html').read_text(encoding='utf-8')
                new_digest = hashlib.sha256(b'new content').hexdigest()[:12]
                self.assertIn(f'src="app.js?v={new_digest}"', new_html)
                self.assertNotIn(f'src="app.js?v={digest}"', new_html)
                (root / 'dark-theme.css').write_text('dark theme updated', encoding='utf-8')
                build_site.build(root / 'dist')
                theme_html = (root / 'dist' / 'index.html').read_text(encoding='utf-8')
                theme_digest = hashlib.sha256(b'dark theme updated').hexdigest()[:12]
                self.assertIn(f'href="dark-theme.css?v={theme_digest}"', theme_html)
                self.assertNotIn(f'href="dark-theme.css?v={digest}"', theme_html)
                (root / 'accessibility.css').write_text('larger text updated', encoding='utf-8')
                build_site.build(root / 'dist')
                accessible_html = (root / 'dist' / 'index.html').read_text(encoding='utf-8')
                accessible_digest = hashlib.sha256(b'larger text updated').hexdigest()[:12]
                self.assertIn(f'href="accessibility.css?v={accessible_digest}"', accessible_html)
                self.assertNotIn(f'href="accessibility.css?v={digest}"', accessible_html)


if __name__ == '__main__':
    unittest.main()
