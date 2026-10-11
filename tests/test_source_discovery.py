"""Automatic source discovery must find SID's abstract page without manual entry.

Fixtures are explicit synthetic copies of the webpage structure, not live
network requests. Publication still requires the current extraction safeguards.
"""
import datetime as dt
import unittest
from pipeline.discovery import discover_abstract_links
from pipeline.core import check_sources, source_targets
from pipeline.auto_publish import publish_changes, official_sources_for

LANDING='https://www.sidnet.org/annualmeeting/'
ABSTRACT='https://www.sidnet.org/annualmeeting/abstracts/'
KEY_DATES='https://www.sidnet.org/annualmeeting/key-dates/'
HOME='''<html><body><h1>Society for Investigative Dermatology 2027 Annual Meeting</h1>
<nav><a href="/annualmeeting/key-dates/">Key Dates</a>
<a href="/annualmeeting/abstracts/">Abstract Information</a>
<a href="/annualmeeting/abstracts/">Abstract Guidelines</a>
<a href="https://evil.example/annualmeeting/abstracts/">Submit Abstracts</a>
<a href="/annualmeeting/2026-abstracts/">2026 Abstracts</a>
<a href="/membership/abstracts/">Abstracts for members</a>
<a href="/annualmeeting/abstract-books/">Abstract Books</a>
<a href="/annualmeeting/hotel/">Hotel Information</a>
</nav><p>SID 2027 annual meeting dates are May 12–15, 2027 in Orlando.</p>
</body></html>'''
ABSTRACT_PAGE='''<html><body><h1>Share Your Science at SID 2027</h1>
<h2>Submission Timeline</h2>
<p>Abstract Submissions Open November 2, 2026, and must be submitted by
11:59 pm Eastern Time (US) on January 12, 2027.
Late-Breaking Abstracts can be submitted March 1 – 18, 2027.</p>
<h3>Abstract Submissions for SID 2026 are now closed</h3>
</body></html>'''
KEY_PAGE='<html><h1>2027 SID Key Dates</h1><p>Registration and abstract information coming soon.</p></html>'

def base_record():
    return {'id':'sid27','name':'Society for Investigative Dermatology Annual Meeting 2027',
            'start':'2027-05-12','end':'2027-05-15',
            'open':None,'deadline':None,'lateOpen':None,'lateDeadline':None,
            'url':LANDING,'guideline':KEY_DATES,'society':'SID','specialty':'Dermatology'}

def mock_pages(url,timeout=14):
    return ({LANDING:HOME,KEY_DATES:KEY_PAGE,ABSTRACT:ABSTRACT_PAGE}[url],True)

class AbstractDiscoveryTests(unittest.TestCase):
    def test_finds_sid_abstract_link_from_homepage(self):
        links=discover_abstract_links(HOME,LANDING,2027)
        self.assertEqual([x['url'] for x in links],[ABSTRACT,KEY_DATES])
        self.assertEqual(links[0]['label'],'Abstract Information')

    def test_rejects_cross_domain_and_unrelated_or_old_event_links(self):
        links=discover_abstract_links(HOME,LANDING,2027,max_links=10)
        self.assertNotIn('https://evil.example/annualmeeting/abstracts/',[x['url'] for x in links])
        self.assertFalse(any('2026' in x['url'] for x in links))
        self.assertFalse(any('/membership/' in x['url'] for x in links))
        self.assertFalse(any('abstract-books' in x['url'] for x in links))

    def test_no_crawl_without_relevant_links(self):
        text='<html><a href="/annualmeeting/hotel/">Book Hotel</a></html>'
        self.assertEqual(discover_abstract_links(text,LANDING,2027),[])

    def test_bounds_to_two_links_and_one_site_hop(self):
        text='''<html><a href="/annualmeeting/abstracts/">Abstract Information</a>
        <a href="/annualmeeting/call-for-abstracts/">Call for Abstracts</a>
        <a href="/annualmeeting/submission-guidelines/">Submission Guidelines</a></html>'''
        links=discover_abstract_links(text,LANDING,2027,max_links=2)
        self.assertEqual(len(links),2)

    def test_full_sid_home_to_discovery_to_four_dates(self):
        data={'conferences':[base_record()],'awards':[]}
        # Crucial reproduction: the dedicated abstracts page is NOT configured.
        self.assertNotIn(ABSTRACT,source_targets(data))
        report,_=check_sources(data,fetcher=mock_pages,delay=0,
                               checked_at='2026-10-10T14:00:00Z')
        self.assertEqual(report['source_count'],3)
        self.assertEqual(len(report['discovered_sources']),1)
        self.assertEqual(report['discovered_sources'][0]['source_url'],ABSTRACT)
        fields={(p['field'],p['proposed_value']) for p in report['proposals']}
        self.assertEqual(fields,{('open','2026-11-02'),('deadline','2027-01-12'),
                                 ('lateOpen','2027-03-01'),('lateDeadline','2027-03-18')})
        self.assertEqual(report['conflicts'],[])
        self.assertEqual(report['source_coverage'][0]['discovered_pages'],1)
        published,summary=publish_changes(data,report,checked_at='2026-10-10T14:00:00Z')
        self.assertEqual(len(summary['published']),4)
        row=published['conferences'][0]
        self.assertEqual(row['deadline'],'2027-01-12')
        self.assertEqual(row['lateDeadline'],'2027-03-18')
        self.assertEqual(row['additionalSources'],[ABSTRACT])
        self.assertIn(ABSTRACT,source_targets(published))
        self.assertIsNone(data['conferences'][0]['deadline'])

    def test_untrusted_discovered_url_without_provenance_is_held(self):
        data={'conferences':[base_record()],'awards':[]}
        report={'schema_version':2,'proposals':[{
             'id':'trial','record_id':'sid27','record_type':'conference',
             'record_name':'SID 2027','field':'deadline','current_value':None,
             'proposed_value':'2027-01-12','source_url':ABSTRACT,
             'evidence':'Abstract submission deadline January 12, 2027',
             'review_status':'requires_human_verification'}],'conflicts':[]}
        _,summary=publish_changes(data,report)
        self.assertEqual(summary['published'],[])
        self.assertIn('Untrusted source',summary['held'][0]['reason'])

    def test_provenance_for_another_meeting_not_allowed(self):
        row=base_record()
        report={'discovered_sources':[{'record_type':'conference','record_id':'other27',
              'source_url':ABSTRACT,'parent_url':LANDING,'link_label':'Abstract Information'}]}
        self.assertNotIn(ABSTRACT,official_sources_for(row,report,'conference','sid27'))

if __name__=='__main__':
    unittest.main()
