import unittest
from pipeline.auto_publish import publish_changes

class AutoPublishTests(unittest.TestCase):
    def setUp(self):
        self.data={'asOf':'2026-10-10','conferences':[{'id':'x','name':'Example Meeting 2027','start':'2027-06-01','open':None,'deadline':'2027-01-01','url':'https://example.org/call','guideline':'https://example.org/guide'}],'awards':[]}
    def proposal(self,field='open',date='2026-10-10',old=None,evidence='Abstract submissions open October 10, 2026',sources=None):
        return {'id':'id1','record_type':'conference','record_id':'x','field':field,'proposed_value':date,'current_value':old,'evidence':evidence,'source_url':'https://example.org/call','corroborating_sources':sources or ['https://example.org/call'],'review_status':'requires_human_verification'}
    def report(self,proposals,conflicts=None):
        return {'schema_version':2,'proposals':proposals,'conflicts':conflicts or []}
    def test_publish_blank_date(self):
        data,result=publish_changes(self.data,self.report([self.proposal()]))
        self.assertEqual(data['conferences'][0]['open'],'2026-10-10')
        self.assertEqual(len(result['published']),1)
        self.assertIsNone(self.data['conferences'][0]['open'])
    def test_joint_registration_and_abstract_announcement_accepted(self):
        p=self.proposal(evidence='Registration & Abstract Submissions Opens October 10, 2026')
        updated,result=publish_changes(self.data,self.report([p]))
        self.assertEqual(updated['conferences'][0]['open'],'2026-10-10')
        self.assertEqual(len(result['published']),1)
    def test_joint_announcement_with_unrelated_date_is_held(self):
        p=self.proposal(evidence='Registration closes October 1, 2026. Abstract Submissions Opens October 10, 2026')
        updated,result=publish_changes(self.data,self.report([p]))
        self.assertEqual(result['published'],[])
    def test_registration_date_held(self):
        _,result=publish_changes(self.data,self.report([self.proposal(evidence='Registration opens October 10, 2026')]))
        self.assertEqual(result['published'],[])
    def test_multi_date_evidence_held(self):
        p=self.proposal(evidence='Abstract submissions open October 10, 2026, and close December 1, 2026')
        _,result=publish_changes(self.data,self.report([p]))
        self.assertEqual(result['published'],[])
    def test_changed_deadline_needs_corroboration(self):
        p=self.proposal(field='deadline',date='2027-01-02',old='2027-01-01',evidence='Abstract submission deadline January 2, 2027')
        _,result=publish_changes(self.data,self.report([p]))
        self.assertEqual(result['published'],[])
        p['corroborating_sources']=['https://example.org/call','https://example.org/guide']
        resultdata,result=publish_changes(self.data,self.report([p]))
        self.assertEqual(resultdata['conferences'][0]['deadline'],'2027-01-02')
    def test_conflicts_held(self):
        p=self.proposal()
        _,result=publish_changes(self.data,self.report([p],conflicts=[{'record_type':'conference','record_id':'x','field':'deadline'}]))
        self.assertEqual(result['published'],[])
    def test_circuit_breaker(self):
        _,result=publish_changes(self.data,self.report([self.proposal()]),max_updates=0)
        self.assertTrue(result['circuit_breaker_triggered'])
        self.assertEqual(result['published'],[])
    def test_official_source_supersedes_tracker_date(self):
        self.data['conferences'][0]['evidence']='tracker'
        p=self.proposal(field='deadline',date='2027-01-02',old='2027-01-01',evidence='Abstract submission deadline January 2, 2027')
        updated,result=publish_changes(self.data,self.report([p]))
        self.assertEqual(updated['conferences'][0]['deadline'],'2027-01-02')
        self.assertEqual(len(result['published']),1)
    def test_official_source_cannot_override_conflicting_official_pages(self):
        self.data['conferences'][0]['evidence']='tracker'
        p=self.proposal(field='deadline',date='2027-01-02',old='2027-01-01',evidence='Abstract submission deadline January 2, 2027')
        conflict={'record_type':'conference','record_id':'x','field':'deadline'}
        updated,result=publish_changes(self.data,self.report([p],conflicts=[conflict]))
        self.assertEqual(updated['conferences'][0]['deadline'],'2027-01-01')
        self.assertEqual(result['published'],[])
    def test_unexpected_schema_rejected(self):
        with self.assertRaises(ValueError):
            publish_changes(self.data,{'schema_version':1,'proposals':[]})
if __name__=='__main__':unittest.main()
