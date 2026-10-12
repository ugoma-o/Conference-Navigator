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
    def test_cost_tile_replaces_abstract_quick_check(self):
        self.assertIn('class="detail-block conference-cost-detail"',self.js)
        self.assertIn('<div class="detail-label">Conference costs</div>',self.js)
        self.assertIn('Registration</span>',self.js)
        self.assertIn('Abstract submission</span>',self.js)
        self.assertIn("c.registrationFee||'Not verified'",self.js)
        self.assertIn("c.fee||'Not verified'",self.js)
        self.assertIn("safeExternal(c.registrationSource||c.url,'Check official fees')",self.js)
        self.assertNotIn('Abstract length quick-check',self.js)
        self.assertNotIn("get('abstractText')",self.js)
        self.assertNotIn('id="counterResult"',self.js)

    def test_costs_are_sixth_tile_in_conference_details_grid(self):
        grid=self.js.index('<div class="modal-section-title">Conference details</div><div class="modal-grid">')
        labels=[
            "detail('Abstract submissions open'",
            "detail('Regular abstract deadline'",
            "detail('Late-breaking deadline'",
            "detail('Length requirement'",
            "detail('Meeting location'",
            '<div class="detail-block conference-cost-detail">'
        ]
        positions=[self.js.index(label,grid) for label in labels]
        self.assertEqual(positions,sorted(positions))
        notes=self.js.index('<div class="modal-section-title">Important notes</div>')
        categories=self.js.index('<div class="modal-section-title">Submission categories and presentation formats</div>')
        self.assertLess(positions[-1],notes)
        self.assertLess(notes,categories)
        self.assertIn('.cost-detail-row{',self.css)

    def test_planner_project_type_has_no_step_one_or_slanted_arrow(self):
        self.assertIn('for="planType">PROJECT TYPE</label>',self.html)
        self.assertNotIn('STEP 1',self.html)
        self.assertNotIn('<span class="awaiting-icon">↗</span>',self.js)
        self.assertIn("get('planType').addEventListener('change',generatePlan)",self.js)

    def test_header_is_project_name(self):
        self.assertIn('<span class="workspace-title"><span class="workspace-rise">RISE</span><span class="workspace-name">Conference Navigator</span></span>',self.html)
        self.assertIn('.workspace-rise{',self.css)
        self.assertIn('.workspace-name{',self.css)
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
        self.assertIn("state.status='all';",self.js)
        self.assertIn("state.sort='meeting';",self.js)
        self.assertIn("get('clearAllFilters').addEventListener('click',clearAllConferenceFilters)",self.js)
        self.assertIn("get('statusFilter').value='all'",self.js)
        self.assertIn("if(state.status==='all')return true",self.js)
        self.assertIn('<option value="active">Active opportunities</option>',self.html)

    def test_multi_day_meeting_bar_not_hidden_by_next_day(self):
        # Pediatric Academic Societies runs Fri Apr 30 through Mon May 3:
        # the Fri–Sat segment must not vanish beneath Saturday meeting cells.
        import json
        from datetime import date, timedelta
        data=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))
        pas=next(c for c in data['conferences'] if c['id']=='pas27')
        start=date.fromisoformat(pas['start'])
        end=date.fromisoformat(pas['end'])
        self.assertLessEqual(start,date(2027,5,1))
        self.assertGreaterEqual(end,date(2027,5,1))
        self.assertIn('for(let d=begin;d<=end;d=shift(d,1))',self.js)
        self.assertIn('if(prev)return',self.js)
        self.assertIn('width:calc(${span*100}% - 14px)',self.js)
        for weekday in range(1,8):
            selector=f'.day-cell.has-ribbon:nth-child(7n + {weekday})'
            self.assertIn(selector,self.css)
        self.assertIn('.day-cell.has-ribbon:focus-within{z-index:20}',self.css)

    def test_research_roadmap_exports_visual_and_calendar(self):
        # Keep .ics export available while ensuring the whole roadmap can
        # be downloaded as vector artwork or printed to a PDF.
        for ident in ('downloadPlan', 'downloadPlanVisual', 'printPlanPdf'):
            with self.subTest(ident=ident):
                self.assertEqual(self.dom.counts.get(ident), 1)
        self.assertIn('function roadmapExportSvg(plan)', self.js)
        self.assertIn('function downloadRoadmapVisual()', self.js)
        self.assertIn('function printRoadmapPdf()', self.js)
        self.assertIn("'image/svg+xml;charset=utf-8'", self.js)
        self.assertIn("get('downloadPlanVisual').addEventListener('click',downloadRoadmapVisual)",self.js)
        self.assertIn("get('printPlanPdf').addEventListener('click',printRoadmapPdf)",self.js)
        self.assertIn('get(\'downloadPlanVisual\').disabled=true', self.js)
        self.assertIn('get(\'printPlanPdf\').disabled=true', self.js)
        self.assertIn('step.desc', self.js)
        self.assertIn('plan.target', self.js)
        self.assertIn("Save as PDF", self.html)
        self.assertIn("Download visual (.svg)", self.html)

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
