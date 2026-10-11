"""Regression tests for the browser-local abstract matching engine."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]

class IDs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
    def handle_starttag(self,tag,attrs):
        ident=dict(attrs).get('id')
        if ident:
            self.ids.add(ident)

@unittest.skipUnless(shutil.which('node'), "Node.js is required for JavaScript matching regressions")
class AbstractMatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'abstract-matcher.js').read_text(encoding='utf-8')

    def run_js(self,code):
        return subprocess.run(['node','-e',code],capture_output=True,text=True,
                              cwd=ROOT,check=True,timeout=25).stdout.strip()

    def test_module_parses_as_javascript(self):
        result=subprocess.run(['node','--check','abstract-matcher.js'],cwd=ROOT,
                              capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_topic_normalization_and_specialty_ranking(self):
        script=r"""
const m=require('./abstract-matcher.js');
const records=[
 {id:'r',name:'Radiation Oncology Research Symposium',specialty:'Radiation Oncology',society:'Society A',url:'https://example.org/rt',types:['Original research'],submissionCategoriesVerified:true},
 {id:'n',name:'Neurosurgery Annual Meeting',specialty:'Neurosurgery',society:'Society B',url:'https://example.org/ns',types:['Original research'],submissionCategoriesVerified:true},
 {id:'d',name:'Dermatology Annual Meeting',specialty:'Dermatology',society:'Society C',url:'https://example.org/derm',types:['Original research'],submissionCategoriesVerified:true}
];
const p='We assessed glioblastoma patients receiving proton therapy radiotherapy using magnetic resonance imaging. Tumor imaging and clinical progression were evaluated prospectively using a longitudinal cohort. Outcomes were compared following multi institutional analysis.';
const r=m.matchAbstract(p,records,{today:'2026-10-11'});
console.log(JSON.stringify({topics:r.topics,first:r.results[0].id,ids:r.results.map(x=>x.id)}));
"""
        out=json.loads(self.run_js(script))
        self.assertIn('Brain tumors',out['topics'])
        self.assertIn('Radiotherapy',out['topics'])
        self.assertEqual(out['first'],'r')
        self.assertIn('n',out['ids'])

    def test_case_report_detection_and_format_verification_guard(self):
        script=r"""
const m=require('./abstract-matcher.js');
const text='This case report describes a rare complication in a patient with psoriasis who developed an unusual cutaneous eruption following medical management. The clinical findings and longitudinal follow up are described.';
const records=[{id:'d',name:'Dermatology Society Meeting',specialty:'Dermatology',
 society:'Dermatology Society',url:'https://example.org/derm',
 types:['Original research'],submissionCategoriesVerified:false}];
const found=m.matchAbstract(text,records,{today:'2026-10-11'});
console.log(JSON.stringify({format:found.format,fit:found.results[0].fit.status,topics:found.topics}));
"""
        out=json.loads(self.run_js(script))
        self.assertEqual(out['format'],'case')
        self.assertEqual(out['fit'],'unverified')
        self.assertIn('Dermatology',out['topics'])

    def test_dates_never_become_abstract_eligibility_proof(self):
        script=r"""
const m=require('./abstract-matcher.js');
const c={id:'x',name:'Neurology Conference',specialty:'Neurology',society:'Neurology Society',
 url:'https://example.org/n',open:'2026-10-01',deadline:'2026-11-01',
 lateOpen:'2027-01-01',lateDeadline:'2027-01-14',submissionCategoriesVerified:false};
const before=m.opportunity(c,'2026-10-11');
const after=m.opportunity(c,'2026-11-15');
const closed=m.opportunity(c,'2027-02-01');
console.log(JSON.stringify([before,after,closed,m.formatFit(c,'case')]));
"""
        out=json.loads(self.run_js(script))
        self.assertEqual([x['status'] for x in out[:3]],['open','upcoming','closed'])
        self.assertEqual(out[3]['status'],'unverified')

    def test_input_has_minimum_quality_threshold(self):
        script=r"""
const m=require('./abstract-matcher.js');
console.log(JSON.stringify(m.matchAbstract('kidney',[],{today:'2026-10-11'})));
"""
        self.assertTrue(json.loads(self.run_js(script))['error'])

class AbstractMatcherIntegrationTests(unittest.TestCase):
    def test_paste_interface_is_present(self):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        parser=IDs()
        parser.feed(html)
        for ident in ('matcherView','matchAbstractText','matchFormat','matchRun',
                      'matchClear','matchOutput','matchShowClosed','matchWordCount'):
            self.assertIn(ident,parser.ids)
        self.assertIn('data-view="matcher"',html)
        self.assertIn('<script src="abstract-matcher.js"></script>',html)
        self.assertIn('autocomplete="off"',html)

    def test_matches_are_not_uploaded_or_persisted(self):
        source=(ROOT/'abstract-matcher.js').read_text(encoding='utf-8')
        app=(ROOT/'app.js').read_text(encoding='utf-8')
        self.assertNotIn('fetch(',source)
        self.assertNotIn('XMLHttpRequest',source)
        self.assertNotIn('localStorage',source)
        self.assertNotIn('sendBeacon',source)
        self.assertIn('escape(why)',app)
        self.assertIn('escape(match.name)',app)
        self.assertIn('RISE_ABSTRACT_MATCHER',app)

    def test_deployment_assets_in_build_allowlist(self):
        build=(ROOT/'pipeline'/'build_site.py').read_text(encoding='utf-8')
        for item in ('abstract-matcher.css','abstract-matcher.js'):
            self.assertIn(item,build)

if __name__=='__main__':
    unittest.main()
