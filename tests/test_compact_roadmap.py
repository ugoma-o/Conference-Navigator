"""Structural checks to prevent vertical timeline bloat and cramped key-date labels."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class CompactRoadmapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=(ROOT/'app.js').read_text(encoding='utf-8')
        cls.style=(ROOT/'accessibility.css').read_text(encoding='utf-8')

    def test_stage_layout_is_compact_and_milestones_are_separate(self):
        self.assertIn('v7-roadmap v8-roadmap',self.script)
        self.assertIn('class="v8-chart-area"',self.script)
        self.assertIn('class="v6-event-labels v8-event-grid"',self.script)
        self.assertIn('class="v8-key-dates-heading">KEY DATES',self.script)
        self.assertIn('Important research planning dates',self.script)
        self.assertIn('.v8-roadmap .v6-stages .roadmap-row',self.style)
        self.assertIn('padding:3px 0 7px!important',self.style)
        self.assertIn('height:16px;min-height:16px',self.style)

    def test_event_labels_are_readable_and_not_absolutely_positioned(self):
        self.assertIn('grid-template-columns:repeat(2,minmax(0,1fr))',self.style)
        self.assertIn('position:static!important',self.style)
        self.assertIn('max-width:none',self.style)
        self.assertIn('height:auto!important',self.style)
        self.assertIn('border:0!important',self.style)
        self.assertIn('font-size:14px',self.style)
        self.assertIn('@media(max-width:580px)',self.style)
        self.assertIn('grid-template-columns:minmax(0,1fr)',self.style)
        self.assertNotIn('style="--event-x:',self.script)

    def test_guides_stay_inside_stage_plot_not_date_summary(self):
        plot_start=self.script.index('<div class="v8-chart-area"><div class="v6-guides">')
        plot_end=self.script.index('<div class="v6-bottom-rail"><div class="v8-key-dates-heading">')
        segment=self.script[plot_start:plot_end]
        self.assertIn('<div class="v6-stages">${barRows}</div></div>',segment)
        self.assertIn('.v8-roadmap .v8-chart-area .v6-guides{inset:9px 0 5px}',self.style)

    def test_date_and_export_logic_remains_intact(self):
        self.assertIn('function roadmapExportSvg(plan){',self.script)
        self.assertIn('function downloadRoadmapVisual(){',self.script)
        self.assertIn('function printRoadmapPdf(){',self.script)
        self.assertIn("fmt(target.internalDay)",self.script)
        self.assertIn("fmt(target.day)",self.script)

if __name__=='__main__':
    unittest.main()
