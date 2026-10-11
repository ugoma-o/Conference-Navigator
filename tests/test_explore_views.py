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
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

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

    def test_conference_modal_is_focused_on_conference_details(self):
        # Conference detail no longer duplicates the interactive Research Planner.
        self.assertNotIn('From idea to presentation',self.js)
        self.assertNotIn("get('modalRoadmapType')",self.js)
        self.assertNotIn('<div class="modal-roadmap">',self.js)
        self.assertNotIn('Choose a project type to explore potential submission categories',self.js)
        self.assertNotIn('id="submissionFit"',self.js)
        self.assertIn("get('presentationOptions').innerHTML=presentationOptions(c)",self.js)
        self.assertIn('Formats confirmed for this meeting:',self.js)
        self.assertIn("get('planConference').value=c.id;state.plan=null;closeModal();nav('planner')",self.js)
    def test_cost_panel_replaces_abstract_quick_check(self):
        self.assertIn('Conference costs',self.js)
        self.assertIn('Registration fee',self.js)
        self.assertIn('Abstract submission fee',self.js)
        self.assertIn("c.registrationFee||'Not verified in RISE'",self.js)
        self.assertIn("c.fee||'Not verified in RISE'",self.js)
        self.assertNotIn('Abstract length quick-check',self.js)
        self.assertNotIn("get('abstractText')",self.js)
        self.assertNotIn('id="counterResult"',self.js)
    def test_planner_project_type_has_no_step_one_or_slanted_arrow(self):
        self.assertIn('for="planType">PROJECT TYPE</label>',self.html)
        self.assertNotIn('STEP 1',self.html)
        self.assertNotIn('<span class="awaiting-icon">↗</span>',self.js)
        self.assertIn("get('planType').addEventListener('change',generatePlan)",self.js)

    def test_header_is_project_name(self):
        self.assertIn('RISE Conference Navigator</span>',self.html)
        self.assertNotIn('id="breadcrumbCurrent"',self.html)
        self.assertNotIn("get('breadcrumbCurrent')",self.js)

    def test_list_defaults_to_all_conferences_including_closed(self):
        # Meeting discovery should not conceal an upcoming meeting simply
        # because its regular abstract deadline has passed (AAD 2027).
        import json
        data=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))
        aad=next(c for c in data['conferences'] if c['id']=='aad27')
        self.assertLess(aad['deadline'],aad['start'])
        self.assertIn('id="statusFilter"',self.html)
        self.assertIn('<option value="all" selected>All conferences</option>',self.html)
        self.assertIn("search:'',status:'all',sort:'meeting'",self.js)
        self.assertIn("state.status='all';state.sort='meeting'",self.js)
        self.assertIn("get('statusFilter').value='all'",self.js)
        self.assertIn("if(state.status==='all')return true",self.js)
        self.assertIn('<option value="active">Active opportunities</option>',self.html)

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
