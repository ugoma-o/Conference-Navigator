"""Deterministic regressions from the first real GitHub run (10 October 2026).

Snippets paraphrase/condense the corresponding official source pages. They are
NOT a live scrape; exact raw data from the GitHub review report is retained by
its original artifact. No fixture itself authorizes publication.
"""
import copy
import unittest
from pipeline.core import check_sources, extract_labeled_dates, textify, approve, draft_cycle

AANS='''<html><h1>2027 AANS Annual Scientific Meeting — abstract center</h1>
<h2>Abstract Center Opens</h2><p>Wednesday, July 22, 2026</p>
<h2>Abstract Center Closes</h2><p>Thursday, October 1, 2026</p>
<h2>Abstract Center Extension</h2><p>Sunday, October 4, 2026 – CLOSED</p>
<p>Abstract submissions open July 22 and close October 5, 2026.</p>
<p>Edits permitted before the submission deadline, October 4, 2026, 11:59PM ET.</p></html>'''
ACG='''<html><h1>ACG Annual Scientific Meeting - Abstracts Closed</h1>
<p>General abstract submission for ACG 2026 is now closed.</p>
<p>The submission deadline was Monday, June 1, 2026, at 11:59 PM.</p></html>'''
SHM='''<html><h1>SHM Converge 2027</h1><p>Scientific abstract competitions</p>
<p>Submissions are open from September 11 through November 23, 2026.</p></html>'''
SGIM='''<html><h1>2027 Southwest Regional Meeting</h1>
<p>2027 meeting will take place January 30, 2027.</p>
<p>Call for Submissions OPEN: August 28, 2026</p>
<p>Call for Submissions CLOSE: October 13, 2026</p></html>'''

class OriginalReportRegressionTests(unittest.TestCase):
    def setUp(self):
        self.data={'conferences':[
            {'id':'aans27','name':'AANS Annual Scientific Meeting 2027','start':'2027-04-09',
             'open':'2026-07-22','deadline':None,'url':'https://example.org/aans'},
            {'id':'acg27','name':'ACG Annual Scientific Meeting 2027','start':None,
             'open':None,'deadline':None,'url':'https://example.org/acg'},
            {'id':'shm27','name':'SHM Converge 2027','start':'2027-03-30',
             'open':'2026-09-11','deadline':'2026-11-23','url':'https://example.org/shm'},
            {'id':'sgimsw27','name':'SGIM Southwest Regional Meeting 2027','start':'2027-01-30',
             'open':None,'deadline':'2026-10-13','url':'https://example.org/sgim'}], 'awards':[]}
        self.pages={'https://example.org/aans':AANS,'https://example.org/acg':ACG,
                    'https://example.org/shm':SHM,'https://example.org/sgim':SGIM}

    def scan(self):
        return check_sources(self.data,fetcher=lambda url,timeout=14:(self.pages[url],True),delay=0)[0]

    def test_aans_three_conflicting_deadlines_are_quarantined(self):
        report=self.scan()
        self.assertFalse(any(x['record_id']=='aans27' for x in report['proposals']))
        conflict=next(x for x in report['conflicts'] if x['record_id']=='aans27' and x['field']=='deadline')
        self.assertEqual(conflict['values'],['2026-10-01','2026-10-04','2026-10-05'])

    def test_aans_opening_is_not_taken_from_close_date(self):
        found=extract_labeled_dates(textify(AANS),'conference',2027)
        opens={x['value'] for x in found if x['field']=='open'}
        self.assertEqual(opens,{'2026-07-22'})

    def test_old_cycle_stays_rejected_even_with_generic_2027_navigation(self):
        page=ACG.replace('<html>', '<html><header>Research newsletter for 2027 members</header>')
        data=copy.deepcopy(self.data)
        pages=dict(self.pages);pages['https://example.org/acg']=page
        report,_=check_sources(data,fetcher=lambda u,timeout=14:(pages[u],True),delay=0)
        self.assertFalse(any(x['record_id']=='acg27' for x in report['proposals']))

    def test_acg_2026_deadline_never_suggested_for_2027(self):
        report=self.scan()
        self.assertFalse(any(x['record_id']=='acg27' for x in report['proposals']))
        self.assertEqual(extract_labeled_dates(textify(ACG),'conference',2027),[])

    def test_shm_range_open_and_close_correct_order(self):
        found=extract_labeled_dates(textify(SHM),'conference',2027)
        self.assertEqual({(h['field'],h['value']) for h in found},
                         {('open','2026-09-11'),('deadline','2026-11-23')})
        self.assertFalse(any(x['record_id']=='shm27' for x in self.scan()['proposals']))

    def test_sgim_only_correct_missing_opening_proposed(self):
        report=self.scan()
        self.assertEqual([(x['record_id'],x['field'],x['proposed_value']) for x in report['proposals']],
                         [('sgimsw27','open','2026-08-28')])

    def test_previous_github_reports_cannot_be_approved_after_upgrade(self):
        report=self.scan()
        report.pop('schema_version')
        report['proposals'].append({'id':'legacy','record_type':'conference','record_id':'acg27',
           'field':'deadline','current_value':None,'proposed_value':'2026-06-01',
           'source_url':'https://example.org/acg','evidence':'Prior year'})
        with self.assertRaisesRegex(ValueError,'Legacy monitoring report'):
            approve(copy.deepcopy(self.data),report,'legacy','Resident Reviewer')

    def test_conflict_prevents_approval_even_with_manipulated_proposal(self):
        report=self.scan()
        report['proposals'].append({'id':'bad','record_type':'conference','record_id':'aans27',
          'field':'deadline','current_value':None,'proposed_value':'2026-10-04',
          'source_url':'https://example.org/aans','evidence':'example'})
        with self.assertRaisesRegex(ValueError,'conflicting official evidence'):
            approve(copy.deepcopy(self.data),report,'bad','Clinical Reviewer')

    def test_conflict_between_two_different_source_urls(self):
        data={'conferences':[{'id':'meeting27','name':'Meeting 2027','start':'2027-05-01',
              'open':None,'deadline':None,'url':'https://example.org/one',
              'guideline':'https://example.org/two'}],'awards':[]}
        pages={'https://example.org/one':'Meeting 2027 scientific abstracts: Important abstract deadline October 8, 2026. Plan your original research presentation and submission requirements carefully.',
               'https://example.org/two':'Meeting 2027 scientific abstracts: Important abstract deadline October 9, 2026. Plan your original research presentation and submission requirements carefully.'}
        report,_=check_sources(data,fetcher=lambda u,timeout=14:(pages[u],False),delay=0)
        self.assertEqual(len(report['proposals']),0)
        self.assertEqual(len(report['conflicts']),1)
        self.assertEqual(report['conflicts'][0]['values'],['2026-10-08','2026-10-09'])

    def test_report_displays_blocked_conflicts(self):
        from pipeline.cli import report_html
        from pathlib import Path
        import tempfile
        report=self.scan()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'queue.html'
            report_html(report,path)
            content=path.read_text()
            self.assertIn('Conflicting official dates',content)
            self.assertIn('2026-10-01',content)
            self.assertIn('2026-10-04',content)
            self.assertIn('2026-10-05',content)
            self.assertIn('BLOCKED',content)

    def test_draft_clears_location_and_previous_year_source(self):
        data={'conferences':[{'id':'meeting27','name':'Meeting 2027','start':'2027-05-01',
                              'end':'2027-05-03','city':'Nashville, TN','venue':'Convention Center',
                              'url':'https://example.org/2027','open':'2026-11-01','deadline':'2027-01-01'}],
              'awards':[]}
        [draft]=draft_cycle(data,2028)
        for field in ('city','venue','url','open','deadline','start','end'):
            self.assertIsNone(draft[field],field)
        self.assertEqual(draft['priorCycleSourceUrl'],'https://example.org/2027')

if __name__=='__main__':unittest.main()
