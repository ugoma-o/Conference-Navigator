"""Regression checks for RISE's unified, accessible editorial identity."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class EditorialStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css=(ROOT/'editorial-design.css').read_text(encoding='utf-8')
        cls.html=(ROOT/'index.html').read_text(encoding='utf-8')
        cls.app=(ROOT/'app.js').read_text(encoding='utf-8')

    def test_one_font_family_for_all_editorial_ui(self):
        self.assertIn("--ed-sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,Helvetica,sans-serif",self.css)
        self.assertIn("html:not([data-design=\"classic\"]) body *:not(svg):not(path)",self.css)
        self.assertIn("font-family:var(--ed-sans) !important",self.css)
        self.assertNotIn("font-family:var(--ed-serif);",self.css)
        self.assertIn("font:700 clamp(26px,3vw,34px)/1.24 var(--ed-sans)",self.css)

    def test_notes_are_plain_text_not_tinted_stripe_boxes(self):
        self.assertIn('Important notes</div><div class="modal-note',self.app)
        scope=self.css.rsplit("html:not([data-design=\"classic\"]) .modal-note,",1)[1]
        self.assertIn("background:transparent;",scope[:470])
        self.assertIn("border:0;",scope[:470])
        self.assertIn("padding:0;",scope[:470])
        self.assertIn("font-size:16px;",scope[:470])
        self.assertIn("color:var(--ed-ink)",scope[:470])

    def test_color_is_structural_and_dark_mode_is_supported(self):
        self.assertIn("--ed-heading:#103a59",self.css)
        self.assertIn("--ed-accent:#008a96",self.css)
        self.assertIn("background:#0b3957",self.css)
        self.assertIn("background:#087e89",self.css)
        self.assertIn('html[data-theme="dark"]:not([data-design="classic"]) .modal-note',self.css)
        self.assertIn('html[data-theme="dark"]:not([data-design="classic"]) .sidebar',self.css)
        self.assertIn("background:#007e8c",self.css)

    def test_old_style_still_available_for_comparison(self):
        self.assertIn('get("design") === "classic"',self.html)
        self.assertIn("""document.querySelector('link[href^="editorial-design.css"]')""",self.html)
        self.assertIn("if (editorialSheet) editorialSheet.disabled = true",self.html)
        self.assertIn('<link rel="stylesheet" href="editorial-design.css" />',self.html)

if __name__=='__main__':
    unittest.main()
