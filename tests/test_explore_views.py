"""Regression checks for the unified conference List / Calendar interface."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Structure(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta',
          'param','source','track','wbr'}

    def __init__(self):
        super().__init__()
        self.stack=[]
        self.parents={}
        self.counts={}
        self.attrs={}

    def handle_starttag(self,tag,attrs):
        properties=dict(attrs)
        ident=properties.get('id')
        if ident:
            self.parents[ident]=[x[1] for x in self.stack if x[1]]
            self.counts[ident]=self.counts.get(ident,0)+1
            self.attrs[ident]=properties
        if tag not in self.VOID:
            self.stack.append((tag,ident))

    def handle_startendtag(self,tag,attrs):
        pass

    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                del self.stack[i:]
                break


class ExploreViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/'index.html').read_text(encoding='utf-8')
        cls.js=(ROOT/'app.js').read_text(encoding='utf-8')
        cls.css=(ROOT/'styles.css').read_text(encoding='utf-8')
        cls.dom=Structure()
        cls.dom.feed(cls.html)

    def test_calendar_embedded_in_explore(self):
        self.assertEqual(self.dom.counts.get('calendarView'),1)
        self.assertIn('discoverView',self.dom.parents['calendarView'])
        self.assertIn('discoverView',self.dom.parents['discoverListPanel'])
        self.assertNotIn('discoverView',self.dom.parents['plannerView'])
        self.assertNotIn('discoverView',self.dom.parents['fundingView'])

    def test_single_explore_nav_and_two_modes(self):
        self.assertNotIn('data-view="calendar"',self.html)
        self.assertIn('data-explore-mode="list"',self.html)
        self.assertIn('data-explore-mode="calendar"',self.html)
        self.assertIn('function setExploreMode(mode)',self.js)
        self.assertIn(".explore-mode-panel:not(.active)",self.css)

    def test_header_is_project_name(self):
        self.assertIn('RISE Conference Navigator</span>',self.html)
        self.assertNotIn('id="breadcrumbCurrent"',self.html)
        self.assertNotIn("get('breadcrumbCurrent')",self.js)

    def test_existing_calendar_controls_retained(self):
        for ident in ('calendarMonth','calendarGrid','calendarJump',
                      'calendarMonthRail','calendarSpecialty','calDeadlines',
                      'calMeetings','calAwards','calendarMonthEventList'):
            with self.subTest(ident=ident):
                self.assertEqual(self.dom.counts.get(ident),1)

    def test_specialty_selection_stays_in_sync(self):
        self.assertIn("state.calSpecialty=s==='All specialties'?'All':s",self.js)
        self.assertIn("state.specialty=state.calSpecialty==='All'?'All specialties':state.calSpecialty",self.js)


if __name__=='__main__':
    unittest.main()
