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
                '<link rel="stylesheet" href="styles.css" />'
                '<script src="data.js"></script><script src="app.js"></script>', encoding='utf-8')
            for filename in ('app.js', 'data.js', 'styles.css'):
                (root / filename).write_text('initial content', encoding='utf-8')
            with patch.object(build_site, 'ROOT', root), patch.object(build_site.subprocess, 'run'):
                build_site.build(root / 'dist')
                html = (root / 'dist' / 'index.html').read_text(encoding='utf-8')
                digest = hashlib.sha256(b'initial content').hexdigest()[:12]
                self.assertIn(f'src="app.js?v={digest}"', html)
                self.assertIn(f'src="data.js?v={digest}"', html)
                self.assertIn(f'href="styles.css?v={digest}"', html)
                (root / 'app.js').write_text('new content', encoding='utf-8')
                build_site.build(root / 'dist')
                new_html = (root / 'dist' / 'index.html').read_text(encoding='utf-8')
                new_digest = hashlib.sha256(b'new content').hexdigest()[:12]
                self.assertIn(f'src="app.js?v={new_digest}"', new_html)
                self.assertNotIn(f'src="app.js?v={digest}"', new_html)


if __name__ == '__main__':
    unittest.main()
