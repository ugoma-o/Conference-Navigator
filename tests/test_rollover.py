import datetime as dt
import unittest
from pipeline.rollover import extract_future_meetings,make_cycle_record
from pipeline.auto_publish import publish_changes

PARENT={'id':'astro27','name':'ASTRO Annual Meeting 2027','society':'ASTRO',
        'specialty':'Oncology','start':'2027-09-18','end':'2027-09-22',
        'url':'https://official.example.org/annual-meeting',
        'deadline':'2027-02-01','open':'2026-10-01','fee':'$300',
        'city':'Chicago, IL','types':['Original research']}

class AnnualCycleTests(unittest.TestCase):
    def scan(self,text):
        return extract_future_meetings(text,PARENT,PARENT['url'],today=dt.date(2026,10,10))
    def test_find_new_annual_meeting(self):
        found=self.scan('ASTRO Annual Meeting 2028: September 22–26, 2028')
        self.assertEqual(len(found),1)
        self.assertEqual((found[0]['record_id'],found[0]['start'],found[0]['end']),('astro28','2028-09-22','2028-09-26'))
    def test_no_guess(self):
        self.assertEqual(self.scan('ASTRO Annual Meeting 2028 dates to be announced.'),[])
    def test_ignore_other_society_and_submeeting(self):
        self.assertEqual(self.scan('AAPM Annual Meeting 2028: September 22–26, 2028'),[])
    def test_ignore_tentative(self):
        self.assertEqual(self.scan('ASTRO Annual Meeting 2028 tentative September 22–26, 2028'),[])
    def test_do_not_reuse_year_specific_url(self):
        parent={**PARENT,'url':'https://official.example.org/annual-meeting/2027'}
        self.assertEqual(extract_future_meetings('ASTRO Annual Meeting 2028: September 22–26, 2028',parent,parent['url'],today=dt.date(2026,10,10)),[])
    def test_publish_creates_clean_cycle(self):
        p=self.scan('ASTRO Annual Meeting 2028: September 22–26, 2028')[0]
        data={'conferences':[PARENT.copy()],'awards':[]}
        updated,summary=publish_changes(data,{'schema_version':2,'proposals':[],'conflicts':[],'future_candidates':[p]},checked_at='2026-10-10T00:00:00Z')
        self.assertEqual(len(updated['conferences']),2)
        future=updated['conferences'][1]
        self.assertEqual(future['start'],'2028-09-22')
        for field in ('open','deadline','lateOpen','lateDeadline','fee'):
            self.assertIsNone(future[field])
        self.assertEqual(future['city'],'To be announced')
        self.assertEqual(len(summary['published']),1)
        self.assertEqual(len(data['conferences']),1)
    def test_skip_existing_cycle(self):
        p=self.scan('ASTRO Annual Meeting 2028: September 22–26, 2028')[0]
        data={'conferences':[PARENT.copy(),{**PARENT,'id':'astro28','name':'ASTRO Annual Meeting 2028'}],'awards':[]}
        updated,summary=publish_changes(data,{'schema_version':2,'proposals':[],'conflicts':[],'future_candidates':[p]})
        self.assertEqual(len(updated['conferences']),2)
        self.assertEqual(summary['published'],[])

if __name__=='__main__':unittest.main()
