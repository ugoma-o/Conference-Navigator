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
        self.assertIn("--ed-heading:#0b334f",self.css)
        self.assertIn("--ed-accent:#007d88",self.css)
        self.assertIn("background:#0b3957",self.css)
        self.assertIn("background:#087e89",self.css)
        self.assertIn('html[data-theme="dark"]:not([data-design="classic"]) .modal-note',self.css)
        self.assertIn('html[data-theme="dark"]:not([data-design="classic"]) .sidebar',self.css)
        self.assertIn("background:#007e8c",self.css)

    def test_strong_structural_brand_elements(self):
        self.assertIn('/* 12. RISE SIGNATURE PALETTE',self.css)
        self.assertIn('--rise-navy:#0b3553',self.css)
        self.assertIn('--rise-teal:#006975',self.css)
        self.assertIn('--rise-copper:#91530f',self.css)
        self.assertIn('background:var(--rise-navy)',self.css)
        self.assertIn('background:#006975',self.css)
        self.assertIn('border-bottom:3px solid var(--rise-teal-bright)',self.css)
        self.assertIn('horizon-month.selected .horizon-count-row strong',self.css)
        self.assertIn('background:var(--ed-paper)',self.css)
        self.assertIn('color:var(--rise-header-text)',self.css)
        self.assertIn('html[data-theme="dark"]',self.css)

    def test_no_layout_change_to_roadmap(self):
        from hashlib import sha256
        css=(ROOT/'accessibility.css').read_text(encoding='utf-8')
        js=(ROOT/'app.js').read_text(encoding='utf-8')
        self.assertIn('.v7-roadmap .v6-event-label.conference',css)
        self.assertIn('top:calc(var(--event-row) * 49px - 62px)!important',css)
        self.assertIn('function roadmapMarkup(',js)

    def test_contrast_for_brand_text(self):
        def luminance(color):
            vals=[int(color[i:i+2],16)/255 for i in (1,3,5)]
            linear=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in vals]
            return sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))
        def contrast(a,b):
            x,y=sorted([luminance(a),luminance(b)],reverse=True)
            return (x+.05)/(y+.05)
        self.assertGreaterEqual(contrast('#006975','#ffffff'),4.5)
        self.assertGreaterEqual(contrast('#0b3553','#ffffff'),7)
        self.assertGreaterEqual(contrast('#91530f','#ffffff'),4.5)

    def test_old_style_still_available_for_comparison(self):
        self.assertIn('get("design") === "classic"',self.html)
        self.assertIn("""document.querySelector('link[href^="editorial-design.css"]')""",self.html)
        self.assertIn("if (editorialSheet) editorialSheet.disabled = true",self.html)
        self.assertIn('<link rel="stylesheet" href="editorial-design.css" />',self.html)

if __name__=='__main__':
    unittest.main()
