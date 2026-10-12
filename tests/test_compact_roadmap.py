"""Protect the original spacious research timeline from compact-layout regressions."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class RoadmapLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=(ROOT/'app.js').read_text(encoding='utf-8')
        cls.style=(ROOT/'accessibility.css').read_text(encoding='utf-8')

    def test_original_long_stage_rows_and_event_track(self):
        self.assertIn('roadmap-block v6-roadmap v7-roadmap',self.script)
        self.assertIn('class="v6-canvas"><div class="v6-guides">${guides}</div>',self.script)
        self.assertIn('class="v6-stages">${barRows}</div>',self.script)
        self.assertIn('class="v6-event-labels">${eventFlags}</div>',self.script)
        self.assertIn('.v6-stages .roadmap-row{min-height:78px}',self.style)
        self.assertIn('.v6-event-labels{height:240px}',self.style)
        self.assertNotIn('v8-roadmap',self.script)
        self.assertNotIn('v9-roadmap',self.script)
        self.assertNotIn('v10-roadmap',self.script)

    def test_timeline_uses_date_aligned_benchmark_markers(self):
        markup=self.script[self.script.index('function roadmapMarkup('):
                           self.script.index('function roadmapExportSvg(')]
        self.assertIn("guide('today',todayPct)",markup)
        self.assertIn("guide('opening',openPct)",markup)
        self.assertIn("guide('conference',meetingPct)",markup)
        self.assertIn('style="--event-x:${x.toFixed(2)}%;--event-row:${row}"',markup)
        self.assertIn("marker('internal','Aim to submit'",markup)
        self.assertIn("marker('conference','Conference'",markup)
        self.assertIn("marker('opening','Submissions open'",markup)
        self.assertNotIn('v10-key-dates',markup)

    def test_roadmap_exports_still_available(self):
        self.assertIn('function roadmapExportSvg(plan){',self.script)
        self.assertIn('function downloadRoadmapVisual(){',self.script)
        self.assertIn('function printRoadmapPdf(){',self.script)
        self.assertIn("fmt(target.internalDay)",self.script)
        self.assertIn("fmt(target.day)",self.script)


if __name__=='__main__':
    unittest.main()
