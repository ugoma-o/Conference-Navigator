"""Outlook selection must show actual submission events within the clicked month.

Many 2027 conferences have 2026 abstract deadlines, so matching a month
does not mean the conference itself takes place in that month.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('node'),"Requires Node to execute the actual month selection code")
class OutlookMonthTests(unittest.TestCase):
    def run_javascript(self,source):
        proc=subprocess.run(['node','-e',source],cwd=ROOT,text=True,
                            capture_output=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stderr)
        return json.loads(proc.stdout)

    @staticmethod
    def helpers():
        return r"""
const fs=require('fs');
const app=fs.readFileSync('./app.js','utf8');
const start=app.indexOf("function monthMatches(c,m,type='all'){");
const end=app.indexOf('function horizonMonths(){',start);
if(start<0||end<0)throw new Error('Month matching implementation missing');
const helpers=new Function('key','fmt','dateRange',app.slice(start,end)+';return {monthMatches,matchesMonth};');
const {monthMatches,matchesMonth}=helpers(
    d=>String(d.getFullYear())+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'),
    d=>d,
    (a,b)=>a===b?a:a+' to '+b);
"""

    def test_october_abstract_due_for_2027_meeting(self):
        script=self.helpers()+r"""
const c={id:'meeting',name:'Society Meeting 2027',
         start:'2027-03-01',end:'2027-03-04',open:'2026-08-05',
         deadline:'2026-10-14',lateOpen:null,lateDeadline:null};
const october=monthMatches(c,'2026-10');
const march=monthMatches(c,'2027-03');
const november=monthMatches(c,'2026-11');
console.log(JSON.stringify({october,march,november,selected:matchesMonth(c,'2026-10')}));
"""
        value=self.run_javascript(script)
        self.assertEqual([(e['kind'],e['label'],e['day']) for e in value['october']],
                         [('due','Abstract deadline','2026-10-14')])
        self.assertEqual([e['kind'] for e in value['march']],['meeting'])
        self.assertFalse(value['november'])
        self.assertTrue(value['selected'])

    def test_late_breaking_and_meeting_across_month_boundary(self):
        script=self.helpers()+r"""
const c={start:'2026-09-29',end:'2026-10-03',deadline:'2026-09-12',
         lateDeadline:'2026-10-12',lateOpen:'2026-10-01'};
const ev=monthMatches(c,'2026-10');
console.log(JSON.stringify(ev));
"""
        value=self.run_javascript(script)
        self.assertEqual([(e['kind'],e['day']) for e in value],
                         [('open','2026-10-01'),('meeting','2026-10-01'),('due','2026-10-12')])
        self.assertIn('2026-09-29',value[1]['display'])

    def test_same_day_repeated_regular_late_dates_not_double_counted(self):
        script=self.helpers()+r"""
const c={open:'2026-10-04',lateOpen:'2026-10-04',
         deadline:'2026-10-29',lateDeadline:'2026-10-29'};
console.log(JSON.stringify(monthMatches(c,'2026-10')));
"""
        value=self.run_javascript(script)
        self.assertEqual([v['kind'] for v in value],['open','due'])

    def test_real_database_outlook_counts_link_to_relevant_meetings(self):
        script=self.helpers()+r"""
const db=require('./data.json');
const oct=db.conferences.map(c=>({c,events:monthMatches(c,'2026-10')}))
  .filter(x=>x.events.length);
const all=oct.flatMap(x=>x.events);
const misplaced=oct.filter(x=>x.events.every(e=>e.day.substring(0,7)!=='2026-10'));
const future=oct.filter(x=>x.c.start&&x.c.start>'2026-10-31');
console.log(JSON.stringify({matching:oct.length,due:all.filter(x=>x.kind==='due').length,
open:all.filter(x=>x.kind==='open').length,
meetings:all.filter(x=>x.kind==='meeting').length,
misplaced:misplaced.length,future:future.length,examples:future.slice(0,4).map(x=>({name:x.c.name,events:x.events}))}));
"""
        report=self.run_javascript(script)
        self.assertGreater(report['matching'],0)
        self.assertEqual(report['misplaced'],0)
        self.assertGreater(report['future'],0)
        self.assertGreater(report['due'],0)


    def test_date_type_filters_are_exclusive(self):
        script=self.helpers()+r"""
const c={start:'2027-05-07',end:'2027-05-09',open:'2026-10-01',
         deadline:'2026-10-18',lateOpen:'2026-10-20',lateDeadline:'2026-10-30'};
const types=['all','meeting','open','deadline','lateOpen','lateDeadline'];
const selected={};
for(const t of types)selected[t]=monthMatches(c,'2026-10',t).map(x=>x.field);
selected.meetingInMay=monthMatches(c,'2027-05','meeting').map(x=>x.field);
selected.noMonth=monthMatches(c,null,'deadline').map(x=>x.day);
console.log(JSON.stringify(selected));
"""
        found=self.run_javascript(script)
        self.assertEqual(found['meeting'],[])
        self.assertEqual(found['open'],['open'])
        self.assertEqual(found['deadline'],['deadline'])
        self.assertEqual(found['lateOpen'],['lateOpen'])
        self.assertEqual(found['lateDeadline'],['lateDeadline'])
        self.assertEqual(found['meetingInMay'],['meeting'])
        self.assertEqual(found['noMonth'],['2026-10-18'])
        self.assertEqual(len(found['all']),4)

    def test_one_unified_date_and_sort_control(self):
        app=(ROOT/'app.js').read_text(encoding='utf-8')
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertEqual(html.count('id="dateTypeFilter"'),1)
        self.assertNotIn('id="sortFilter"',html)
        self.assertNotIn('id="monthSortOption"',html)
        for kind in ('all','meeting','open','deadline','lateOpen','lateDeadline','name'):
            self.assertIn(f'<option value="{kind}"',html)
        self.assertIn("get('dateTypeFilter').addEventListener('change',applyDateView)",app)
        self.assertIn("state.dateType=view==='name'?'all':view",app)
        self.assertIn("state.sort=view==='name'?'name':(state.monthKey||state.dateType!=='all'?'month':'meeting')",app)
        self.assertIn("matchesMonth(c,state.monthKey,state.dateType)",app)
        self.assertIn("get('dateTypeFilter').value='all'",app)
        self.assertNotIn("get('sortFilter')",app)
        self.assertNotIn("get('monthSortOption')",app)

    def test_month_context_and_filtered_rows_are_visible(self):
        app=(ROOT/'app.js').read_text(encoding='utf-8')
        self.assertIn('MATCHING ',app)
        self.assertIn("'Filtered by '+DATE_TYPE_NAMES[state.dateType]",app)
        self.assertIn("const monthEvents=list.flatMap(c=>monthMatches(c,m,state.dateType))",app)
        self.assertIn("function selectOutlookMonth(next){state.monthKey=next;applyDateView()}",app)

if __name__=='__main__':
    unittest.main()
