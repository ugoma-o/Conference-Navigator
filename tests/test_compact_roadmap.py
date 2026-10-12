"""Regressions for a readable research roadmap and chart-aligned date guides."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class CompactRoadmapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=(ROOT/'app.js').read_text(encoding='utf-8')
        cls.style=(ROOT/'accessibility.css').read_text(encoding='utf-8')

    def test_stage_spacing_remains_compact(self):
        self.assertIn('v7-roadmap v8-roadmap v10-roadmap',self.script)
        self.assertIn('class="v6-canvas v10-canvas"',self.script)
        self.assertIn('class="v8-chart-area v10-chart-area"',self.script)
        self.assertIn('padding:3px 0 7px!important',self.style)
        self.assertIn('height:16px;min-height:16px',self.style)

    def test_timeline_guides_do_not_pass_through_milestone_text(self):
        markup=self.script[self.script.index('function roadmapMarkup('):
                           self.script.index('function roadmapExportSvg(')]
        chart=markup.index('<div class="v8-chart-area v10-chart-area">')
        guides=markup.index('<div class="v6-guides">${guides}</div>')
        stages=markup.index('<div class="v6-stages">${barRows}</div>')
        legend=markup.index('<div class="v6-bottom-rail">')
        self.assertLess(chart,guides)
        self.assertLess(guides,stages)
        self.assertLess(stages,legend)
        self.assertIn('.v10-roadmap .v10-chart-area > .v6-guides',self.style)
        self.assertIn('inset:6px 0 0!important',self.style)
        self.assertIn("guide('today',todayPct)",markup)
        self.assertIn("guide('internal',internalPct)",markup)
        self.assertIn("guide('opening',openPct)",markup)
        self.assertIn("guide('conference',meetingPct)",markup)
        self.assertIn('class="v10-key-dates" aria-label="Timeline date legend"',markup)
        self.assertNotIn('v9-event-track',markup)

    def test_date_labels_have_space_and_matching_colors(self):
        self.assertIn('class="v10-milestone ${ev.klass}"',self.script)
        self.assertIn('class="v10-milestone-copy"',self.script)
        self.assertIn('<time>${escape(fmt(ev.day))}</time>',self.script)
        self.assertIn('grid-template-columns:repeat(2,minmax(0,1fr))',self.style)
        self.assertIn('min-height:68px',self.style)
        self.assertIn('font-size:15px!important',self.style)
        self.assertIn('grid-template-columns:minmax(0,1fr)',self.style)
        for color in ('opening','internal','deadline','conference'):
            self.assertIn('.v10-roadmap .v10-milestone.'+color,self.style)
        self.assertIn('html[data-theme="dark"] .v10-roadmap',self.style)
        self.assertNotIn('top:calc(var(--event-row)',self.style)
        self.assertNotIn('left:clamp(min(110px',self.style)

    def test_date_and_export_logic_are_unchanged(self):
        self.assertIn('function roadmapExportSvg(plan){',self.script)
        self.assertIn('function downloadRoadmapVisual(){',self.script)
        self.assertIn('function printRoadmapPdf(){',self.script)
        self.assertIn("fmt(target.internalDay)",self.script)
        self.assertIn("fmt(target.day)",self.script)

if __name__=='__main__':
    unittest.main()
