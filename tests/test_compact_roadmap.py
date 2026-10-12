"""Regression checks for readable, date-aligned research roadmap benchmarks."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class CompactRoadmapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=(ROOT/'app.js').read_text(encoding='utf-8')
        cls.style=(ROOT/'accessibility.css').read_text(encoding='utf-8')

    def test_stages_remain_compact_but_benchmarks_reappear(self):
        self.assertIn('v7-roadmap v8-roadmap v9-roadmap',self.script)
        self.assertIn('class="v6-canvas v9-canvas" style="--event-count:',self.script)
        self.assertIn('class="v8-chart-area"',self.script)
        self.assertIn('class="v6-event-labels v9-event-track"',self.script)
        self.assertIn('class="v8-key-dates-heading">KEY DATES',self.script)
        self.assertIn('Date benchmarks on the project timeline',self.script)
        self.assertIn('padding:3px 0 7px!important',self.style)
        self.assertIn('height:16px;min-height:16px',self.style)

    def test_vertical_guides_extend_to_bottom_labels(self):
        markup=self.script[self.script.index('function roadmapMarkup('):
                           self.script.index('function roadmapExportSvg(')]
        self.assertIn("guide('today',todayPct)",markup)
        self.assertIn("guide('internal',internalPct)",markup)
        self.assertIn("guide('opening',openPct)",markup)
        self.assertIn("guide('conference',meetingPct)",markup)
        plot_guides=markup.index('<div class="v6-canvas v9-canvas"')
        chart=markup.index('<div class="v8-chart-area">')
        bottom=markup.index('<div class="v6-bottom-rail">')
        self.assertLess(plot_guides,chart)
        self.assertLess(chart,bottom)
        self.assertIn('class="v6-guides">${guides}</div><div class="v8-chart-area">',markup)
        self.assertIn('.v9-roadmap .v9-canvas > .v6-guides',self.style)
        self.assertIn('inset:8px 0 3px!important',self.style)

    def test_date_labels_have_independent_rows_and_edge_clamping(self):
        self.assertIn("const events=[",self.script)
        self.assertIn('].filter(Boolean);',self.script)
        self.assertIn('--event-row:${i}',self.script)
        self.assertIn('--event-x:${ev.x.toFixed(2)}%',self.script)
        self.assertIn('width:min(220px, calc(100% - 12px))',self.style)
        self.assertIn('left:clamp(min(110px, 50%), var(--event-x), max(calc(100% - 110px), 50%))!important',self.style)
        self.assertIn('height:calc(var(--event-count) * var(--benchmark-row-height) + 3px)!important',self.style)
        self.assertIn('top:calc(var(--event-row) * var(--benchmark-row-height) + 3px)!important',self.style)
        self.assertIn('white-space:normal',self.style)
        self.assertIn('.v9-roadmap .v9-event-track .v6-event-label small',self.style)
        self.assertIn('@media(max-width:580px)',self.style)
        self.assertIn('html[data-theme="dark"] .v9-roadmap',self.style)

    def test_date_and_export_logic_remains_intact(self):
        self.assertIn('function roadmapExportSvg(plan){',self.script)
        self.assertIn('function downloadRoadmapVisual(){',self.script)
        self.assertIn('function printRoadmapPdf(){',self.script)
        self.assertIn("fmt(target.internalDay)",self.script)
        self.assertIn("fmt(target.day)",self.script)

if __name__=='__main__':
    unittest.main()
