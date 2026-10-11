"""Accessibility and deployment regressions for the opt-in light/dark appearance toggle."""
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons={}
        self.links=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='button' and d.get('id'):
            self.buttons[d['id']]=d
        if tag=='link' and d.get('rel')=='stylesheet':
            self.links.append(d.get('href'))

class ThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/'index.html').read_text(encoding='utf-8')
        cls.css=(ROOT/'styles.css').read_text(encoding='utf-8')
        cls.dark=(ROOT/'dark-theme.css').read_text(encoding='utf-8')
        cls.js=(ROOT/'app.js').read_text(encoding='utf-8')

    def test_accessible_toggle_and_theme_persistence(self):
        p=Controls()
        p.feed(self.html)
        button=p.buttons['themeToggle']
        self.assertEqual(button.get('type'),'button')
        self.assertEqual(button.get('aria-pressed'),'false')
        self.assertIn('dark-theme.css',p.links)
        self.assertIn('styles.css',p.links)
        self.assertLess(p.links.index('styles.css'),p.links.index('dark-theme.css'))
        self.assertIn("localStorage.getItem('rise-theme')",self.html)
        self.assertIn("localStorage.setItem('rise-theme',next)",self.js)
        self.assertIn("applyTheme(document.documentElement.dataset.theme",self.js)
        self.assertIn("button.setAttribute('aria-pressed',String(dark))",self.js)
        self.assertIn("button.setAttribute('aria-label',title)",self.js)
        self.assertIn("const next=document.documentElement.dataset.theme==='dark'?'light':'dark'",self.js)
        self.assertIn("get('themeToggleText').textContent=dark?'Light mode':'Dark mode'",self.js)

    def test_dark_colors_only_appear_when_opted_in(self):
        self.assertIn('html[data-theme="dark"]',self.dark)
        self.assertIn('color-scheme:dark;',self.dark)
        self.assertIn("--bg:#0c1622",self.dark)
        self.assertIn('.day-cell',self.dark)
        self.assertIn('.calendar-grid .meeting-ribbon',self.dark)
        self.assertIn('.roadmap-lane',self.dark)
        self.assertIn('.funding-card',self.dark)
        self.assertIn('.modal',self.dark)
        self.assertIn('.calendar-day-dialog',self.dark)
        self.assertIn('.status-pill',self.dark)
        self.assertIn('@media(max-width:470px)',self.dark)
        self.assertIn('.theme-toggle{',self.dark)

    def test_production_build_copies_and_versions_theme(self):
        from pipeline.build_site import build
        with TemporaryDirectory() as tmp:
            out=Path(tmp)
            build(out)
            self.assertTrue((out/'dark-theme.css').is_file())
            self.assertEqual((out/'dark-theme.css').read_text(encoding='utf-8'),self.dark)
            html=(out/'index.html').read_text(encoding='utf-8')
            self.assertIn('dark-theme.css?v=',html)
            self.assertIn('styles.css?v=',html)
            self.assertIn('data.js?v=',html)
            self.assertIn('app.js?v=',html)
            self.assertFalse((out/'pipeline').exists())

if __name__=='__main__':
    unittest.main()
