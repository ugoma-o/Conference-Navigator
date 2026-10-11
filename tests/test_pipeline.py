import copy
import json
from pathlib import Path
import tempfile
import unittest
from pipeline.core import ROOT, check_sources, extract_labeled_dates, approve, draft_cycle, validate, textify
from pipeline.cli import report_html

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.data={'asOf':'2026-10-10','conferences':[
            {'id':'acro27','name':'ACRO 2027','society':'ACRO','specialty':'Radiation oncology',
             'start':'2027-02-18','end':'2027-02-21','open':'2026-08-14','deadline':'2026-10-09',
             'url':'https://acro.org/page/abstracts','evidence':'official'},
        ],'awards':[
            {'id':'grant','name':'Travel grant 2027','conferenceId':'acro27','society':'ACRO',
             'open':None,'deadline':None,'url':'https://acro.org/page/travel'}]}
        self.first='''<html><body><h1>Submit Your Abstract for ACRO 2027</h1>
          <p>Submission portals for both the physician and SEAL programs open August 14, 2026.</p>
          <p>The deadline to submit is October 9, 2026. No extension.</p></body></html>'''
    def fetcher(self, pages):
        def f(url,timeout=14):return (pages[url],True)
        return f
    def test_extract_2027_acro_2026_deadlines(self):
        fields={(v['field'],v['value']) for v in extract_labeled_dates(textify(self.first), 'conference',2027)}
        self.assertIn(('open','2026-08-14'),fields)
        self.assertIn(('deadline','2026-10-09'),fields)
    def test_sid_main_annual_meeting_abstract_opening_detected(self):
        from pipeline.auto_publish import publish_changes
        official_url='https://www.sidnet.org/annualmeeting/'
        meeting={'id':'sid27','name':'Society for Investigative Dermatology Annual Meeting 2027',
                 'start':'2027-05-12','end':'2027-05-15','open':None,'deadline':None,
                 'url':official_url,'society':'Society for Investigative Dermatology',
                 'specialty':'Dermatology'}
        data={'conferences':[meeting],'awards':[]}
        page='<html><h1>2027 SID Annual Meeting</h1><p>May 12-15, 2027 Orlando</p><h3>Registration & Abstract Submissions Opens November 2, 2026</h3></html>'
        report,_=check_sources(data,fetcher=self.fetcher({official_url:page}),delay=0,
                               checked_at='2026-10-10T12:00:00Z')
        self.assertEqual([(p['field'],p['proposed_value']) for p in report['proposals']],
                         [('open','2026-11-02')])
        changed,audit=publish_changes(data,report,checked_at='2026-10-10T12:00:00Z')
        self.assertEqual(changed['conferences'][0]['open'],'2026-11-02')
        self.assertEqual(len(audit['published']),1)
        self.assertIsNone(changed['conferences'][0]['deadline'])
    def test_sid_dedicated_abstract_page_all_four_dates(self):
        from pipeline.auto_publish import publish_changes
        source='https://www.sidnet.org/annualmeeting/abstracts/'
        data={'conferences':[{
            'id':'sid27','name':'Society for Investigative Dermatology Annual Meeting 2027',
            'society':'Society for Investigative Dermatology','specialty':'Dermatology',
            'start':'2027-05-12','end':'2027-05-15',
            'open':None,'deadline':None,'lateOpen':None,'lateDeadline':None,
            'url':'https://www.sidnet.org/annualmeeting/','submissionSource':source
        }],'awards':[]}
        sample='''<h1>Share Your Science at SID 2027</h1>
        <h3>Submission Timeline</h3>
        <p>Abstract Submissions Open November 2, 2026, and must be submitted by
        11:59 pm Eastern Time (US) on January 12, 2027.
        Late-Breaking Abstracts can be submitted March 1 – 18, 2027.
        See detailed timeline below.</p>
        <h2>Abstract Submissions for SID 2026 are now closed.</h2>'''
        report,_=check_sources(data,fetcher=self.fetcher({source:sample,
            data['conferences'][0]['url']:'<h1>SID 2027 Annual Meeting</h1><p>Meeting May 12-15, 2027, Orlando.</p>'}),
            delay=0,checked_at='2026-10-10T20:00:00Z')
        found={(p['field'],p['proposed_value']) for p in report['proposals']}
        self.assertEqual(found,{
            ('open','2026-11-02'),('deadline','2027-01-12'),
            ('lateOpen','2027-03-01'),('lateDeadline','2027-03-18')})
        self.assertEqual(report['conflicts'],[])
        updated,summary=publish_changes(data,report,checked_at='2026-10-10T20:00:00Z')
        row=updated['conferences'][0]
        self.assertEqual((row['open'],row['deadline'],row['lateOpen'],row['lateDeadline']),
                         ('2026-11-02','2027-01-12','2027-03-01','2027-03-18'))
        self.assertEqual(len(summary['published']),4)

    def test_short_late_breaking_range_not_regular_abstract_deadline(self):
        page='SID 2027: Late-Breaking Abstracts can be submitted March 1 – 18, 2027.'
        dates=extract_labeled_dates(page,'conference',2027)
        self.assertEqual({(v['field'],v['value']) for v in dates},
                         {('lateOpen','2027-03-01'),('lateDeadline','2027-03-18')})
    def test_undated_submit_by_must_not_be_guessed(self):
        page='SID 2027. Abstract submissions open November 2 and must be submitted by January 12.'
        self.assertEqual(extract_labeled_dates(page,'conference',2027),[])

    def test_sid_key_dates_without_explicit_close_must_not_guess(self):
        t=textify('<h1>Important Deadlines for the 2027 SID Annual Meeting</h1>'
                  '<p>Mark your calendar for abstract submission, registration, travel grants and hotel booking.</p>')
        self.assertEqual(extract_labeled_dates(t,'conference',2027),[])
    def test_baseline_and_stable_and_change(self):
        pages={'https://acro.org/page/abstracts':self.first,
               'https://acro.org/page/travel':'<html><body><h1>ACRO trainee award</h1><p>Award applications open November 1, 2026. Application deadline November 16, 2026.</p></body></html>'}
        report,cache=check_sources(self.data,fetcher=self.fetcher(pages),delay=0,checked_at='2026-10-10T20:00:00Z')
        self.assertEqual(report['counts']['baseline'],2)
        self.assertTrue(any(p['record_type']=='award' for p in report['proposals']))
        report2,cache2=check_sources(self.data,cache=cache,fetcher=self.fetcher(pages),delay=0)
        self.assertEqual(report2['counts']['unchanged'],2)
        changed=dict(pages);changed['https://acro.org/page/abstracts']=self.first.replace('October 9, 2026','October 12, 2026')
        report3,_=check_sources(self.data,cache=cache2,fetcher=self.fetcher(changed),delay=0)
        self.assertEqual(report3['counts']['changed'],1)
        p=next(x for x in report3['proposals'] if x['record_id']=='acro27')
        self.assertEqual((p['field'],p['current_value'],p['proposed_value']),('deadline','2026-10-09','2026-10-12'))
        self.assertEqual(self.data['conferences'][0]['deadline'],'2026-10-09')
        updated=copy.deepcopy(self.data)
        audit=approve(updated,report3,p['id'],'Resident Administrator',timestamp='2026-10-11T12:00:00Z')
        self.assertEqual(updated['conferences'][0]['deadline'],'2026-10-12')
        self.assertEqual(updated['asOf'],'2026-10-11')
        self.assertEqual(audit['reviewer'],'Resident Administrator')
        with self.assertRaises(ValueError):approve(updated,report3,p['id'],'Resident Administrator')
    def test_ambiguous_dates_not_proposed(self):
        pages={'https://acro.org/page/abstracts':'<h1>ACRO 2027 abstracts</h1><p>Abstract deadline October 9, 2026.</p><p>Abstract deadline October 14, 2026.</p>',
               'https://acro.org/page/travel':'<p>No date has been announced for grant</p>'}
        r,_=check_sources(self.data,fetcher=self.fetcher(pages),delay=0)
        self.assertFalse(any(x['record_id']=='acro27' and x['field']=='deadline' for x in r['proposals']))
    def test_no_year_guess(self):
        self.assertEqual(extract_labeled_dates('Abstract submissions open August 14. Abstract deadline October 9.', 'conference', 2027),[])
    def test_multiple_years_filtered(self):
        t='Abstract deadline October 1, 2025. Abstract deadline October 9, 2026. ACRO 2027.'
        self.assertEqual({x['value'] for x in extract_labeled_dates(t,'conference',2027)},{'2026-10-09'})
    def test_unavailable_is_not_record_update(self):
        def fail(url,timeout=14):raise ValueError('blocked')
        r,_=check_sources(self.data,fetcher=fail,delay=0)
        self.assertEqual(r['counts']['unavailable'],2)
        self.assertEqual(r['proposals'],[])
    def test_annual_draft_no_fabricated_dates(self):
        drafts=draft_cycle(self.data,2028)
        self.assertEqual(len(drafts),1)
        c=drafts[0]
        self.assertEqual(c['id'],'acro28')
        self.assertIsNone(c['start'])
        self.assertIsNone(c['deadline'])
        self.assertIsNone(c['open'])
        self.assertEqual(c['evidence'],'unannounced')
        self.assertIsNone(c['limitType'])
        self.assertEqual(self.data['conferences'][0]['start'],'2027-02-18')
    def test_prevent_bad_edit(self):
        report={'schema_version':2,'proposals':[{'id':'123','record_type':'conference','record_id':'acro27','field':'open',
                'current_value':'2026-08-14','proposed_value':'2026-11-12','source_url':'https://acro.org/page/abstracts','evidence':'one source'}]}
        with self.assertRaisesRegex(ValueError,'Opening cannot'):approve(copy.deepcopy(self.data),report,'123','Resident Admin')
    def test_no_xss_report(self):
        report={'checked_at':'2026-10-10','source_count':1,'checks':[],'proposals':[{
            'id':'abc','record_name':'<script>alert(1)</script>','field':'open','current_value':None,
            'proposed_value':'2026-10-10','source_url':'https://example.com/?x=1&y=2','evidence':'<img src=x onerror=alert(1)>'}]}
        with tempfile.TemporaryDirectory() as tmp:
            dst=Path(tmp)/'report.html';report_html(report,dst);s=dst.read_text()
            self.assertIn('&lt;script&gt;',s)
            self.assertNotIn('<img src=x',s)
    def test_real_dataset_valid(self):
        data=json.loads((ROOT/'data.json').read_text())
        self.assertTrue(validate(data))
        self.assertGreaterEqual(len(data['conferences']),66)

if __name__=='__main__':unittest.main()

class EndToEndTests(unittest.TestCase):
    def test_approved_change_builds_into_live_js_without_changing_baseline(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('data.json','data.js','sync_data.py'):
                (root/name).write_bytes((ROOT/name).read_bytes())
            (root/'pipeline').mkdir()
            for name in ('__init__.py','core.py','cli.py'):
                (root/'pipeline'/name).write_bytes((ROOT/'pipeline'/name).read_bytes())
            data=json.loads((root/'data.json').read_text())
            rec=next(c for c in data['conferences'] if c['id']=='acro27')
            old=rec['deadline']
            self.assertIsNotNone(old)
            proposed='2026-10-08' if old != '2026-10-08' else '2026-10-09'
            from pipeline.core import short_id
            pid=short_id('conference','acro27','deadline',proposed,rec['url'])
            report={'schema_version':2,'proposals':[{'id':pid,'record_type':'conference','record_id':'acro27',
                     'field':'deadline','current_value':old,'proposed_value':proposed,
                     'source_url':rec['url'],'evidence':f'Abstract deadline {proposed}'}]}
            reportfile=root/'report.json';reportfile.write_text(json.dumps(report))
            subprocess.run([sys.executable,'-m','pipeline.cli','approve','--candidate',pid,
                '--reviewer','Pipeline QA','--report',str(reportfile),'--apply'],cwd=root,check=True,capture_output=True)
            revised=json.loads((root/'data.json').read_text())
            edited=next(c for c in revised['conferences'] if c['id']=='acro27')
            self.assertEqual(edited['deadline'],proposed)
            self.assertEqual(edited['fieldSources']['deadline']['reviewed_by'],'Pipeline QA')
            self.assertIn('"deadline": "'+proposed+'"',(root/'data.js').read_text())
            self.assertIn('Pipeline QA',(root/'pipeline'/'approved_changes.jsonl').read_text())
            unchanged=json.loads((ROOT/'data.json').read_text())
            self.assertEqual(next(c for c in unchanged['conferences'] if c['id']=='acro27')['deadline'],old)
